import pytest
from unittest.mock import MagicMock, patch
from langchain_core.runnables import Runnable
from chains.section_highlighter import build_section_highlighter_chain
from chains.skills_matcher import build_skills_matcher_chain
from chains.summary_writer import build_summary_writer_chain
from chains.improver import build_improver_chain


def make_mock_llm():
    """Return a mock that passes isinstance(llm, BaseChatModel) duck-typing."""
    mock = MagicMock()
    mock.__or__ = lambda self, other: MagicMock(spec=Runnable)
    return mock


def test_build_section_highlighter_chain_returns_runnable():
    mock_llm = make_mock_llm()
    chain = build_section_highlighter_chain(mock_llm)
    assert chain is not None


def test_build_skills_matcher_chain_returns_runnable():
    mock_llm = make_mock_llm()
    chain = build_skills_matcher_chain(mock_llm)
    assert chain is not None


def test_build_summary_writer_chain_returns_runnable():
    mock_llm = make_mock_llm()
    chain = build_summary_writer_chain(mock_llm)
    assert chain is not None


def test_build_improver_chain_returns_runnable():
    mock_llm = make_mock_llm()
    chain = build_improver_chain(mock_llm)
    assert chain is not None


def test_section_highlighter_chain_invokes_with_correct_keys():
    """Chain must accept the input keys that the prompt expects."""
    try:
        from langchain_core.language_models.fake_chat_models import FakeListChatModel
    except ImportError:
        from langchain_core.language_models.fake import FakeListChatModel
    from prompts import Resume_Section_Highlighter_Output
    # FakeListChatModel returns pre-set responses without real API calls
    fake_response = '{"plan": [], "additional_steps": [], "work": [], "final_answer": []}'
    llm = FakeListChatModel(responses=[fake_response])
    chain = build_section_highlighter_chain(llm)
    inputs = {
        "duties": "Build software",
        "qualifications": "5 years exp",
        "technical_skills": "Python",
        "non_technical_skills": "Communication",
        "section": "Led backend development of payment system",
    }
    # Should not raise — chain accepts these keys
    result = chain.invoke(inputs)
    assert result is not None
