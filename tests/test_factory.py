import pytest
from unittest.mock import patch
from llm.factory import create_llm
from langchain_openai import ChatOpenAI


def test_create_llm_returns_openai_by_default():
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test'}):
        llm = create_llm()
        assert isinstance(llm, ChatOpenAI)


def test_create_llm_openai_explicit():
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test'}):
        llm = create_llm(provider="openai", model_name="gpt-4o")
        assert isinstance(llm, ChatOpenAI)
        assert llm.model_name == "gpt-4o"


def test_create_llm_uses_env_model_name():
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test', 'OPENAI_MODEL_NAME': 'gpt-4o-mini'}):
        llm = create_llm(provider="openai")
        assert llm.model_name == "gpt-4o-mini"


def test_create_llm_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        create_llm(provider="unknown_provider")
