import hashlib
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Application
    app_name: str = "Squad Nous Chatbot"
    debug: bool = False

    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "squad_nous"
    session_ttl_seconds: int = 3600

    # LLM Provider: "azure_openai" or "openai"
    llm_provider: str = "azure_openai"

    # Azure OpenAI
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_deployment: str = ""

    # Standard OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Prompt config
    prompt_config_path: str = "config/prompt.yaml"


class PromptConfig:
    """Loads and caches the prompt YAML configuration."""

    def __init__(self, path: str):
        self.path = Path(path)
        self._raw: dict = {}
        self._system_prompt: str = ""
        self._schema_version: str = ""
        self.reload()

    def reload(self):
        with open(self.path, encoding="utf-8") as f:
            self._raw = yaml.safe_load(f)
        self._system_prompt = self._raw.get("system_prompt", "")
        self._schema_version = hashlib.sha256(
            self._system_prompt.encode("utf-8")
        ).hexdigest()[:12]

    @property
    def system_prompt(self) -> str:
        return self._system_prompt

    @property
    def schema_version(self) -> str:
        return self._schema_version

    @property
    def title(self) -> str:
        return self._raw.get("title", "Insurance Quote")

    @property
    def description(self) -> str:
        return self._raw.get("description", "I'll collect a few details and then our team will prepare a personalized quote for you.")

    @property
    def raw(self) -> dict:
        return self._raw


@lru_cache
def get_settings() -> Settings:
    return Settings()
