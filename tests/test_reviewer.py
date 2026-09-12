import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# ReviewerOutput model tests
# ---------------------------------------------------------------------------

def test_reviewer_output_passed_true():
    from prompts import ReviewerOutput
    r = ReviewerOutput(passed=True, issues=[], revision_instruction="", corrected_content="")
    assert r.passed is True
    assert r.issues == []
    assert r.revision_instruction == ""
    assert r.corrected_content == ""


def test_reviewer_output_passed_false_with_issues():
    from prompts import ReviewerOutput
    r = ReviewerOutput(
        passed=False,
        issues=["Highlight exceeds 25 words (actual: 38)"],
        revision_instruction="Shorten to one concise sentence under 25 words starting with an action verb.",
        corrected_content="Built payment API reducing checkout latency by 40%.",
    )
    assert r.passed is False
    assert len(r.issues) == 1
    assert "25 words" in r.issues[0]
    assert r.corrected_content != ""


def test_reviewer_output_missing_field_raises():
    from prompts import ReviewerOutput
    with pytest.raises(ValidationError):
        ReviewerOutput(passed=True)  # missing issues, revision_instruction, corrected_content


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_pipeline_stub():
    from pipeline import Pipeline
    p = Pipeline.__new__(Pipeline)
    p.ai_config = {}
    return p


def make_passed_review():
    from prompts import ReviewerOutput
    return ReviewerOutput(passed=True, issues=[], revision_instruction="", corrected_content="")


def make_failed_review(corrected="Fixed bullet line."):
    from prompts import ReviewerOutput
    return ReviewerOutput(
        passed=False,
        issues=["Too long"],
        revision_instruction="Shorten it.",
        corrected_content=corrected,
    )


# ---------------------------------------------------------------------------
# _review_and_correct tests
# ---------------------------------------------------------------------------

def test_review_and_correct_passes_on_first_try():
    """If reviewer passes, writer is called once and result returned unchanged."""
    writer_chain = MagicMock()
    writer_result = MagicMock()
    writer_result.final_answer = "Reduced latency by 40% via caching."
    writer_chain.ainvoke = AsyncMock(return_value=writer_result)

    reviewer_chain = MagicMock()
    reviewer_chain.ainvoke = AsyncMock(return_value=make_passed_review())

    p = make_pipeline_stub()
    apply_correction = MagicMock()

    result = asyncio.run(p._review_and_correct(
        writer_chain=writer_chain,
        reviewer_chain=reviewer_chain,
        inputs={"section": "Built APIs"},
        extract_content=lambda r: r.final_answer,
        apply_correction=apply_correction,
        section_type="highlight",
    ))

    assert result is writer_result
    assert writer_chain.ainvoke.call_count == 1
    assert reviewer_chain.ainvoke.call_count == 1
    apply_correction.assert_not_called()


def test_review_and_correct_applies_correction_when_failed():
    """If reviewer fails, apply_correction is called with corrected_content."""
    writer_chain = MagicMock()
    writer_result = MagicMock()
    writer_result.final_answer = "A very long sentence that has way too many words."
    writer_chain.ainvoke = AsyncMock(return_value=writer_result)

    corrected_text = "Built payment API reducing latency by 40%."
    reviewer_chain = MagicMock()
    reviewer_chain.ainvoke = AsyncMock(return_value=make_failed_review(corrected=corrected_text))

    corrected_result = MagicMock()
    apply_correction = MagicMock(return_value=corrected_result)

    p = make_pipeline_stub()

    result = asyncio.run(p._review_and_correct(
        writer_chain=writer_chain,
        reviewer_chain=reviewer_chain,
        inputs={"section": "Built APIs"},
        extract_content=lambda r: r.final_answer,
        apply_correction=apply_correction,
        section_type="highlight",
    ))

    assert result is corrected_result
    apply_correction.assert_called_once_with(writer_result, corrected_text)
    assert writer_chain.ainvoke.call_count == 1   # writer called only once
    assert reviewer_chain.ainvoke.call_count == 1


def test_review_and_correct_falls_back_when_no_corrected_content(caplog):
    """If reviewer fails but corrected_content is empty, original result is returned with warning."""
    import logging
    from prompts import ReviewerOutput

    writer_chain = MagicMock()
    writer_result = MagicMock()
    writer_chain.ainvoke = AsyncMock(return_value=writer_result)

    reviewer_chain = MagicMock()
    reviewer_chain.ainvoke = AsyncMock(return_value=ReviewerOutput(
        passed=False,
        issues=["Too long"],
        revision_instruction="Shorten it.",
        corrected_content="",  # reviewer failed to provide correction
    ))

    p = make_pipeline_stub()
    apply_correction = MagicMock()

    with caplog.at_level(logging.WARNING):
        result = asyncio.run(p._review_and_correct(
            writer_chain=writer_chain,
            reviewer_chain=reviewer_chain,
            inputs={"section": "Built APIs"},
            extract_content=lambda r: r.final_answer,
            apply_correction=apply_correction,
            section_type="highlight",
        ))

    assert result is writer_result
    apply_correction.assert_not_called()
    assert any("no corrected_content" in record.message.lower() or
               "provided no corrected_content" in record.message
               for record in caplog.records)


def test_review_and_correct_passes_previous_feedback_as_none():
    """reviewer.ainvoke must receive previous_feedback='None' (string)."""
    writer_chain = MagicMock()
    writer_result = MagicMock()
    writer_result.final_answer = "Short bullet."
    writer_chain.ainvoke = AsyncMock(return_value=writer_result)

    reviewer_chain = MagicMock()
    reviewer_chain.ainvoke = AsyncMock(return_value=make_passed_review())

    p = make_pipeline_stub()

    asyncio.run(p._review_and_correct(
        writer_chain=writer_chain,
        reviewer_chain=reviewer_chain,
        inputs={"section": "Built APIs"},
        extract_content=lambda r: r.final_answer,
        apply_correction=MagicMock(),
        section_type="highlight",
    ))

    call_kwargs = reviewer_chain.ainvoke.call_args[0][0]
    assert call_kwargs["previous_feedback"] == "None"


# ---------------------------------------------------------------------------
# Integration: _rewrite_experience_async and update_summary wire-up
# ---------------------------------------------------------------------------

def test_rewrite_experience_uses_review_and_correct():
    """_rewrite_experience_async must call _review_and_correct, not writer directly."""
    from pipeline import Pipeline

    p = Pipeline.__new__(Pipeline)
    p.ai_config = {}
    p.parsed_job = {
        "duties": ["Build APIs"],
        "qualifications": ["5 years Python"],
        "technical_skills": ["Python"],
        "non_technical_skills": ["Communication"],
    }

    exp_raw = {"name": "Acme", "unedited": True, "summary": "Led API development team."}

    expected_result = MagicMock()
    expected_result.final_answer = [MagicMock(highlight="Led API dev.", relevance=5)]

    review_and_correct_mock = AsyncMock(return_value=expected_result)

    with patch.object(p, '_review_and_correct', review_and_correct_mock), \
         patch.object(p, '_get_llm', return_value=MagicMock()):
        asyncio.run(p._rewrite_experience_async(exp_raw))

    review_and_correct_mock.assert_called_once()
    call_kwargs = review_and_correct_mock.call_args.kwargs
    assert call_kwargs.get("section_type") == "highlight"


def test_update_summary_uses_review_and_correct():
    """update_summary must call _review_and_correct for the summary section."""
    from pipeline import Pipeline

    p = Pipeline.__new__(Pipeline)
    p.ai_config = {}
    p.parsed_job = {
        "company": "Acme Corp",
        "job_summary": "Build software",
        "technical_skills": ["Python"],
        "non_technical_skills": ["Communication"],
    }
    p.resume_builder = {
        "summary": "",
        "summary_raw": "Experienced engineer.",
        "experiences": [],
        "projects": [],
        "skills": [],
        "education": [],
    }

    expected_result = MagicMock()
    expected_result.final_answer = "Experienced software engineer with 5 years building scalable APIs."

    review_and_correct_mock = AsyncMock(return_value=expected_result)

    with patch.object(p, '_review_and_correct', review_and_correct_mock), \
         patch.object(p, '_get_llm', return_value=MagicMock()), \
         patch.object(p, '_get_degrees', return_value=[]), \
         patch.object(p, '_format_projects_for_prompt', return_value=[]), \
         patch.object(p, '_format_experiences_for_prompt', return_value=[]), \
         patch.object(p, '_format_skills_for_prompt', return_value=[]):
        p.update_summary()

    review_and_correct_mock.assert_called_once()
    call_kwargs = review_and_correct_mock.call_args.kwargs
    assert call_kwargs.get("section_type") == "summary"
    assert p.resume_builder["summary"] == expected_result.final_answer
