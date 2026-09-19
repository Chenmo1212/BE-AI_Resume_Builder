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


# ─── DB-first tests ───────────────────────────────────────────────────────────

from unittest.mock import patch, MagicMock


def _make_db_doc(name: str) -> dict:
    """Minimal DB document matching what prompt_loader expects."""
    return {
        "name": name,
        "version": 2,
        "messages": [
            {"role": "system", "content": "You are a DB-loaded assistant."},
            {"role": "human", "content": "Hello {name}"},
        ],
    }


def _make_db_client(doc):
    """Build a mock MongoClient whose collection.find_one returns `doc`."""
    mock_col = MagicMock()
    mock_col.find_one.return_value = doc
    mock_client = MagicMock()
    mock_client.__getitem__.return_value.__getitem__.return_value = mock_col
    return mock_client, mock_col


@patch("llm.prompt_loader.MongoClient")
def test_load_prompt_uses_db_when_record_exists(mock_client_cls):
    mock_client, mock_col = _make_db_client(_make_db_doc("section_highlighter"))
    mock_client_cls.return_value = mock_client

    prompt = load_prompt("section_highlighter")

    assert isinstance(prompt, ChatPromptTemplate)
    mock_col.find_one.assert_called_once_with(
        {"name": "section_highlighter", "is_delete": False}
    )


@patch("llm.prompt_loader.MongoClient")
def test_load_prompt_falls_back_to_yaml_when_db_empty(mock_client_cls):
    mock_client, _ = _make_db_client(None)
    mock_client_cls.return_value = mock_client

    prompt = load_prompt("section_highlighter")

    assert isinstance(prompt, ChatPromptTemplate)
    # Should have loaded from YAML — verify it has real variables
    assert "duties" in prompt.input_variables


@patch("llm.prompt_loader.MongoClient")
def test_load_prompt_falls_back_to_yaml_when_db_raises(mock_client_cls):
    mock_client_cls.side_effect = Exception("Connection refused")

    prompt = load_prompt("section_highlighter")

    assert isinstance(prompt, ChatPromptTemplate)
    assert "duties" in prompt.input_variables


@patch("llm.prompt_loader.MongoClient")
def test_load_prompt_raises_file_not_found_when_no_source(mock_client_cls):
    mock_client, _ = _make_db_client(None)
    mock_client_cls.return_value = mock_client

    with pytest.raises(FileNotFoundError):
        load_prompt("nonexistent_prompt_xyz")
