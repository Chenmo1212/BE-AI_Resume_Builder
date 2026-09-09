import os
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel


def create_llm(provider: str = None, api_key: str = None, base_url: str = None, **kwargs) -> BaseChatModel:
    """
    Factory for LangChain chat models.

    Args:
        provider:  LLM provider name ("openai" or "deepseek").
                   If None, defaults to LLM_PROVIDER env var, falling back to "openai".
        api_key:   Optional API key supplied per-request. Takes priority over env vars
                   when non-empty. Never logged or stored.
        base_url:  Optional base URL (DeepSeek only). Takes priority over env var when
                   non-empty.
        **kwargs:  Passed directly to the provider's LangChain class.
                   Supports model_name, temperature, model_kwargs, cache, etc.

    Returns:
        A LangChain BaseChatModel instance.

    Raises:
        ValueError: If provider is not supported.
        EnvironmentError: If required env vars for the provider are missing and no
                          request-supplied key is given.
    """
    if provider is None:
        provider = os.environ.get("LLM_PROVIDER", "openai").lower()

    # Treat empty string as "not provided"
    request_key = api_key if api_key else None
    request_base_url = base_url if base_url else None

    if provider == "openai":
        model_name = kwargs.pop(
            "model_name",
            os.environ.get("OPENAI_MODEL_NAME", "gpt-3.5-turbo")
        )
        resolved_key = request_key or os.environ.get("OPENAI_API_KEY")
        return ChatOpenAI(model=model_name, api_key=resolved_key, **kwargs)

    elif provider == "deepseek":
        resolved_key = request_key or os.environ.get("DEEPSEEK_API_KEY")
        if not resolved_key:
            raise EnvironmentError("DEEPSEEK_API_KEY environment variable is required for deepseek provider")
        model_name = kwargs.pop(
            "model_name",
            os.environ.get("DEEPSEEK_MODEL_NAME", "deepseek-chat")
        )
        resolved_base_url = request_base_url or os.environ.get(
            "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
        )
        return ChatOpenAI(
            model=model_name,
            api_key=resolved_key,
            base_url=resolved_base_url,
            **kwargs
        )

    raise ValueError(f"Unsupported LLM provider: {provider!r}")
