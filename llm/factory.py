import os
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel


def create_llm(provider: str = "openai", **kwargs) -> BaseChatModel:
    """
    Factory for LangChain chat models.

    Args:
        provider: LLM provider name. Currently only "openai" is supported.
                  Phase 2 will add "deepseek".
        **kwargs: Passed directly to the provider's LangChain class.
                  Supports model_name, temperature, model_kwargs, cache, etc.

    Returns:
        A LangChain BaseChatModel instance.

    Raises:
        ValueError: If provider is not supported.
        EnvironmentError: If required env vars for the provider are missing.
    """
    if provider == "openai":
        model_name = kwargs.pop(
            "model_name",
            os.environ.get("OPENAI_MODEL_NAME", "gpt-3.5-turbo")
        )
        return ChatOpenAI(model=model_name, **kwargs)
    # Phase 2: elif provider == "deepseek": ...
    raise ValueError(f"Unsupported LLM provider: {provider!r}")
