import pytest
from pydantic import ValidationError


def test_reviewer_output_passed_true():
    from prompts import ReviewerOutput
    r = ReviewerOutput(passed=True, issues=[], revision_instruction="")
    assert r.passed is True
    assert r.issues == []
    assert r.revision_instruction == ""


def test_reviewer_output_passed_false_with_issues():
    from prompts import ReviewerOutput
    r = ReviewerOutput(
        passed=False,
        issues=["Highlight exceeds 25 words (actual: 38)"],
        revision_instruction="Shorten to one concise sentence under 25 words starting with an action verb.",
    )
    assert r.passed is False
    assert len(r.issues) == 1
    assert "25 words" in r.issues[0]


def test_reviewer_output_missing_field_raises():
    from prompts import ReviewerOutput
    with pytest.raises(ValidationError):
        ReviewerOutput(passed=True)  # missing issues and revision_instruction


import asyncio
from unittest.mock import MagicMock, AsyncMock


def make_pipeline_stub():
    """Return a minimal Pipeline-like object for testing _review_and_retry."""
    from pipeline import Pipeline
    p = Pipeline.__new__(Pipeline)
    p.ai_config = {}
    return p


def test_review_and_retry_passes_on_first_try():
    """If reviewer passes immediately, writer is called only once."""
    from prompts import ReviewerOutput

    writer_chain = MagicMock()
    writer_result = MagicMock()
    writer_result.final_answer = "Reduced latency by 40% via caching."
    writer_chain.ainvoke = AsyncMock(return_value=writer_result)

    reviewer_chain = MagicMock()
    reviewer_chain.ainvoke = AsyncMock(
        return_value=ReviewerOutput(passed=True, issues=[], revision_instruction="")
    )

    p = make_pipeline_stub()

    result = asyncio.run(p._review_and_retry(
        writer_chain=writer_chain,
        reviewer_chain=reviewer_chain,
        inputs={"section": "Built APIs"},
        extract_content=lambda r: r.final_answer,
        section_type="highlight",
    ))

    assert result is writer_result
    assert writer_chain.ainvoke.call_count == 1
    assert reviewer_chain.ainvoke.call_count == 1


def test_review_and_retry_retries_on_failure_then_passes():
    """Writer is called twice when reviewer fails once then passes."""
    from prompts import ReviewerOutput

    writer_chain = MagicMock()
    writer_result_1 = MagicMock()
    writer_result_1.final_answer = "This is a very long sentence that exceeds the twenty five word limit by quite a lot."
    writer_result_2 = MagicMock()
    writer_result_2.final_answer = "Reduced API latency by 40% via Redis caching."
    writer_chain.ainvoke = AsyncMock(side_effect=[writer_result_1, writer_result_2])

    reviewer_chain = MagicMock()
    reviewer_chain.ainvoke = AsyncMock(side_effect=[
        ReviewerOutput(
            passed=False,
            issues=["Highlight exceeds 25 words"],
            revision_instruction="Shorten to one sentence under 25 words.",
        ),
        ReviewerOutput(passed=True, issues=[], revision_instruction=""),
    ])

    p = make_pipeline_stub()

    result = asyncio.run(p._review_and_retry(
        writer_chain=writer_chain,
        reviewer_chain=reviewer_chain,
        inputs={"section": "Built APIs"},
        extract_content=lambda r: r.final_answer,
        section_type="highlight",
    ))

    assert result is writer_result_2
    assert writer_chain.ainvoke.call_count == 2
    assert reviewer_chain.ainvoke.call_count == 2


def test_review_and_retry_returns_last_result_after_max_retries(caplog):
    """After max_retries=2 failures, last result is returned and a warning is logged."""
    import logging
    from prompts import ReviewerOutput

    writer_chain = MagicMock()
    writer_results = [MagicMock(), MagicMock(), MagicMock()]
    for i, r in enumerate(writer_results):
        r.final_answer = f"result_{i}"
    writer_chain.ainvoke = AsyncMock(side_effect=writer_results)

    reviewer_chain = MagicMock()
    reviewer_chain.ainvoke = AsyncMock(return_value=ReviewerOutput(
        passed=False,
        issues=["Still too long"],
        revision_instruction="Make it shorter.",
    ))

    p = make_pipeline_stub()

    with caplog.at_level(logging.WARNING):
        result = asyncio.run(p._review_and_retry(
            writer_chain=writer_chain,
            reviewer_chain=reviewer_chain,
            inputs={"section": "Built APIs"},
            extract_content=lambda r: r.final_answer,
            section_type="highlight",
            max_retries=2,
        ))

    assert result is writer_results[2]
    assert writer_chain.ainvoke.call_count == 3
    assert any("reviewer" in record.message.lower() or "retry" in record.message.lower()
               for record in caplog.records)


def test_review_and_retry_appends_revision_message_on_retry():
    """On retry, inputs must contain the revision instruction from the reviewer."""
    from prompts import ReviewerOutput

    captured_inputs = []

    async def capture_ainvoke(inputs):
        captured_inputs.append(dict(inputs))
        r = MagicMock()
        r.final_answer = "result"
        return r

    writer_chain = MagicMock()
    writer_chain.ainvoke = AsyncMock(side_effect=capture_ainvoke)

    reviewer_chain = MagicMock()
    reviewer_chain.ainvoke = AsyncMock(side_effect=[
        ReviewerOutput(
            passed=False,
            issues=["Too long"],
            revision_instruction="Shorten to under 25 words.",
        ),
        ReviewerOutput(passed=True, issues=[], revision_instruction=""),
    ])

    p = make_pipeline_stub()

    asyncio.run(p._review_and_retry(
        writer_chain=writer_chain,
        reviewer_chain=reviewer_chain,
        inputs={"section": "Built APIs"},
        extract_content=lambda r: r.final_answer,
        section_type="highlight",
    ))

    # First call has no revision key; second call has revision_instruction key
    assert "revision_instruction" not in captured_inputs[0]
    assert captured_inputs[1].get("revision_instruction") == "Shorten to under 25 words."
