from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""

    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers.

    To add a new provider:
    1. Create a new file in app/services/llm/
    2. Subclass BaseLLMProvider
    3. Implement chat_completion() and parse_structured()
    4. Register in factory.py
    """

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Send messages and get a completion, optionally with tool definitions."""
        ...

    @abstractmethod
    async def parse_structured(
        self,
        messages: list[dict[str, str]],
        response_format: type,
        temperature: float = 0.3,
    ) -> Any:
        """Get a structured response parsed into a Pydantic model."""
        ...
