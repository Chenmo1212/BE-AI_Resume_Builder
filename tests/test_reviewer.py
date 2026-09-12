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
