from app.config import Settings
from app.services.llm.azure_openai import AzureOpenAIProvider
from app.services.llm.base import BaseLLMProvider
from app.services.llm.openai_provider import OpenAIProvider

_PROVIDERS: dict[str, str] = {
    "azure_openai": "AzureOpenAIProvider",
    "openai": "OpenAIProvider",
}


def create_llm_provider(settings: Settings) -> BaseLLMProvider:
    """Factory that creates the configured LLM provider.

    Switch providers by setting LLM_PROVIDER in .env — zero code changes.
    """
    provider_name = settings.llm_provider.lower()

    if provider_name == "azure_openai":
        return AzureOpenAIProvider(
            api_key=settings.azure_openai_api_key,
            endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
            deployment=settings.azure_openai_deployment,
        )
    elif provider_name == "openai":
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )
    else:
        available = list(_PROVIDERS.keys())
        raise ValueError(f"Unknown LLM provider: {provider_name}. Available: {available}")
