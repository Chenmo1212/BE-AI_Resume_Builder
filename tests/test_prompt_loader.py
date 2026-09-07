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
    # system + human + human = 3 messages
    assert len(prompt.messages) == 3
