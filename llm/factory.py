import os
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel


def create_llm(provider: str = None, **kwargs) -> BaseChatModel:
    """
    Factory for LangChain chat models.

    Args:
        provider: LLM provider name ("openai" or "deepseek").
                  If None, defaults to LLM_PROVIDER env var, falling back to "openai".
        **kwargs: Passed directly to the provider's LangChain class.
                  Supports model_name, temperature, model_kwargs, cache, etc.

    Returns:
        A LangChain BaseChatModel instance.

    Raises:
        ValueError: If provider is not supported.
        EnvironmentError: If required env vars for the provider are missing.
    """
    if provider is None:
        provider = os.environ.get("LLM_PROVIDER", "openai").lower()

    if provider == "openai":
        model_name = kwargs.pop(
            "model_name",
            os.environ.get("OPENAI_MODEL_NAME", "gpt-3.5-turbo")
        )
        return ChatOpenAI(model=model_name, **kwargs)
    elif provider == "deepseek":
        api_key = kwargs.pop("api_key", os.environ.get("DEEPSEEK_API_KEY"))
        if not api_key:
            raise EnvironmentError("DEEPSEEK_API_KEY environment variable is required for deepseek provider")
        model_name = kwargs.pop(
            "model_name",
            os.environ.get("DEEPSEEK_MODEL_NAME", "deepseek-chat")
        )
        base_url = kwargs.pop(
            "base_url",
            os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        )
        return ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            **kwargs
        )
    raise ValueError(f"Unsupported LLM provider: {provider!r}")
