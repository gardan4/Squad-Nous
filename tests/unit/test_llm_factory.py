import pytest

from app.config import Settings
from app.services.llm.azure_openai import AzureOpenAIProvider
from app.services.llm.factory import create_llm_provider
from app.services.llm.openai_provider import OpenAIProvider


class TestCreateLLMProvider:
    def test_creates_azure_openai_provider(self):
        settings = Settings(
            llm_provider="azure_openai",
            azure_openai_api_key="test-key",
            azure_openai_endpoint="https://test.openai.azure.com",
            azure_openai_deployment="gpt-4o",
        )
        provider = create_llm_provider(settings)
        assert isinstance(provider, AzureOpenAIProvider)

    def test_creates_openai_provider(self):
        settings = Settings(
            llm_provider="openai",
            openai_api_key="test-key",
            openai_model="gpt-4o",
        )
        provider = create_llm_provider(settings)
        assert isinstance(provider, OpenAIProvider)

    def test_case_insensitive_provider_name(self):
        settings = Settings(
            llm_provider="Azure_OpenAI",
            azure_openai_api_key="key",
            azure_openai_endpoint="https://test.openai.azure.com",
            azure_openai_deployment="gpt-4o",
        )
        provider = create_llm_provider(settings)
        assert isinstance(provider, AzureOpenAIProvider)

    def test_unknown_provider_raises_valueerror(self):
        settings = Settings(llm_provider="unknown_provider")
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            create_llm_provider(settings)
