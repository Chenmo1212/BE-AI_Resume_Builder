import pytest
from langchain_core.prompts import ChatPromptTemplate
from llm.prompt_loader import load_prompt


def test_load_prompt_returns_chat_prompt_template():
    prompt = load_prompt("section_highlighter")
    assert isinstance(prompt, ChatPromptTemplate)


def test_load_prompt_has_expected_variables():
    prompt = load_prompt("section_highlighter")
    variables = prompt.input_variables
    assert "duties" in variables
    assert "qualifications" in variables
    assert "technical_skills" in variables
    assert "non_technical_skills" in variables
    assert "section" in variables


def test_load_prompt_unknown_name_raises():
    with pytest.raises(FileNotFoundError):
        load_prompt("nonexistent_prompt_name")


def test_load_prompt_message_count():
    prompt = load_prompt("section_highlighter")
    # system(1) + human×5 (Job Posting, Master Resume, Instruction, Criteria, Steps)
    # + revision_instruction(1) + format_instructions(1) = 8 messages
    assert len(prompt.messages) == 8


def test_skills_matcher_has_expected_variables():
    prompt = load_prompt("skills_matcher")
    variables = prompt.input_variables
    assert "technical_skills" in variables
    assert "non_technical_skills" in variables
    assert "projects" in variables
    assert "experiences" in variables


def test_summary_writer_has_expected_variables():
    prompt = load_prompt("summary_writer")
    variables = prompt.input_variables
    assert "company" in variables
    assert "job_summary" in variables
    assert "degrees" in variables
    assert "projects" in variables
    assert "experiences" in variables
    assert "skills" in variables


def test_improver_has_expected_variables():
    prompt = load_prompt("improver")
    variables = prompt.input_variables
    assert "duties" in variables
    assert "qualifications" in variables
    assert "technical_skills" in variables
    assert "non_technical_skills" in variables
    assert "summary" in variables
    assert "experiences" in variables
    assert "projects" in variables
    assert "education" in variables
    assert "skills" in variables


