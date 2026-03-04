import logging
from typing import Any

import openai
from openai import AsyncAzureOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.services.llm.base import BaseLLMProvider, LLMResponse

logger = logging.getLogger(__name__)

_RETRYABLE = (openai.APITimeoutError, openai.APIConnectionError, openai.RateLimitError)


class AzureOpenAIProvider(BaseLLMProvider):
    """Azure OpenAI Foundry implementation."""

    def __init__(self, api_key: str, endpoint: str, api_version: str, deployment: str):
        self.client = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
        )
        self.deployment = deployment

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(_RETRYABLE),
    )
    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.deployment,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        tool_calls_data = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls_data.append({
                    "id": tc.id,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                })

        return LLMResponse(
            content=choice.message.content or "",
            tool_calls=tool_calls_data,
            finish_reason=choice.finish_reason or "stop",
            usage=(
                {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                }
                if response.usage
                else {}
            ),
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(_RETRYABLE),
    )
    async def parse_structured(
        self,
        messages: list[dict[str, str]],
        response_format: type,
        temperature: float = 0.3,
    ) -> Any:
        response = await self.client.beta.chat.completions.parse(
            model=self.deployment,
            messages=messages,
            response_format=response_format,
            temperature=temperature,
        )
        return response.choices[0].message.parsed
