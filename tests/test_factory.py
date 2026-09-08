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


def test_create_llm_deepseek_success():
    with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'sk-deepseek-test'}):
        llm = create_llm(provider="deepseek")
        assert isinstance(llm, ChatOpenAI)
        assert llm.model_name == "deepseek-chat"
        assert str(llm.openai_api_base).rstrip("/") == "https://api.deepseek.com"


def test_create_llm_deepseek_custom_model_and_url():
    with patch.dict('os.environ', {
        'DEEPSEEK_API_KEY': 'sk-deepseek-test',
        'DEEPSEEK_MODEL_NAME': 'deepseek-reasoner',
        'DEEPSEEK_BASE_URL': 'https://custom.deepseek.api'
    }):
        llm = create_llm(provider="deepseek")
        assert isinstance(llm, ChatOpenAI)
        assert llm.model_name == "deepseek-reasoner"
        assert str(llm.openai_api_base).rstrip("/") == "https://custom.deepseek.api"


def test_create_llm_deepseek_missing_api_key_raises():
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(EnvironmentError, match="DEEPSEEK_API_KEY"):
            create_llm(provider="deepseek")


def test_create_llm_uses_llm_provider_env_var():
    with patch.dict('os.environ', {
        'LLM_PROVIDER': 'deepseek',
        'DEEPSEEK_API_KEY': 'sk-deepseek-test'
    }):
        llm = create_llm()
        assert isinstance(llm, ChatOpenAI)
        assert llm.model_name == "deepseek-chat"


def test_create_llm_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        create_llm(provider="unknown_provider")
