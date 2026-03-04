from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.llm.azure_openai import AzureOpenAIProvider
from app.services.llm.openai_provider import OpenAIProvider


def _make_chat_response(content="Hello", tool_calls=None, finish_reason="stop", usage=None):
    """Build a fake openai ChatCompletion response object."""
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(message=message, finish_reason=finish_reason)
    return SimpleNamespace(choices=[choice], usage=usage)


def _make_tool_call(tc_id, name, arguments):
    fn = SimpleNamespace(name=name, arguments=arguments)
    return SimpleNamespace(id=tc_id, function=fn)


class TestOpenAIProvider:
    @pytest.mark.asyncio
    async def test_chat_completion_basic(self):
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o")
        fake_response = _make_chat_response(content="Hi there")
        provider.client = MagicMock()
        provider.client.chat.completions.create = AsyncMock(return_value=fake_response)

        result = await provider.chat_completion(
            messages=[{"role": "user", "content": "Hello"}]
        )
        assert result.content == "Hi there"
        assert result.tool_calls == []
        assert result.finish_reason == "stop"
        assert result.usage == {}

    @pytest.mark.asyncio
    async def test_chat_completion_with_tool_calls(self):
        provider = OpenAIProvider(api_key="test-key")
        tc = _make_tool_call("call_1", "extract_data", '{"name": "John"}')
        fake_response = _make_chat_response(content="", tool_calls=[tc])
        provider.client = MagicMock()
        provider.client.chat.completions.create = AsyncMock(return_value=fake_response)

        result = await provider.chat_completion(
            messages=[{"role": "user", "content": "test"}],
            tools=[{"type": "function", "function": {"name": "extract_data"}}],
        )
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["function"]["name"] == "extract_data"
        assert result.tool_calls[0]["id"] == "call_1"

    @pytest.mark.asyncio
    async def test_chat_completion_with_usage(self):
        provider = OpenAIProvider(api_key="test-key")
        usage = SimpleNamespace(prompt_tokens=10, completion_tokens=20)
        fake_response = _make_chat_response(content="Hi", usage=usage)
        provider.client = MagicMock()
        provider.client.chat.completions.create = AsyncMock(return_value=fake_response)

        result = await provider.chat_completion(
            messages=[{"role": "user", "content": "test"}]
        )
        assert result.usage == {"prompt_tokens": 10, "completion_tokens": 20}

    @pytest.mark.asyncio
    async def test_chat_completion_null_content(self):
        provider = OpenAIProvider(api_key="test-key")
        fake_response = _make_chat_response(content=None)
        provider.client = MagicMock()
        provider.client.chat.completions.create = AsyncMock(return_value=fake_response)

        result = await provider.chat_completion(
            messages=[{"role": "user", "content": "test"}]
        )
        assert result.content == ""

    @pytest.mark.asyncio
    async def test_parse_structured(self):
        provider = OpenAIProvider(api_key="test-key")
        parsed_obj = {"title": "Test", "fields": []}
        msg = SimpleNamespace(parsed=parsed_obj)
        choice = SimpleNamespace(message=msg)
        fake_response = SimpleNamespace(choices=[choice])
        provider.client = MagicMock()
        provider.client.beta.chat.completions.parse = AsyncMock(return_value=fake_response)

        result = await provider.parse_structured(
            messages=[{"role": "user", "content": "test"}],
            response_format=dict,
        )
        assert result == parsed_obj


class TestAzureOpenAIProvider:
    @pytest.mark.asyncio
    async def test_chat_completion_basic(self):
        provider = AzureOpenAIProvider(
            api_key="test-key",
            endpoint="https://test.openai.azure.com",
            api_version="2024-10-21",
            deployment="gpt-4o",
        )
        fake_response = _make_chat_response(content="Azure says hi")
        provider.client = MagicMock()
        provider.client.chat.completions.create = AsyncMock(return_value=fake_response)

        result = await provider.chat_completion(
            messages=[{"role": "user", "content": "Hello"}]
        )
        assert result.content == "Azure says hi"
        assert result.tool_calls == []

    @pytest.mark.asyncio
    async def test_chat_completion_with_tool_calls(self):
        provider = AzureOpenAIProvider(
            api_key="key", endpoint="https://test.openai.azure.com",
            api_version="2024-10-21", deployment="gpt-4o",
        )
        tc = _make_tool_call("call_az", "extract_data", '{"field": "value"}')
        fake_response = _make_chat_response(content="", tool_calls=[tc])
        provider.client = MagicMock()
        provider.client.chat.completions.create = AsyncMock(return_value=fake_response)

        result = await provider.chat_completion(
            messages=[{"role": "user", "content": "test"}],
            tools=[{"type": "function", "function": {"name": "extract_data"}}],
        )
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["id"] == "call_az"

    @pytest.mark.asyncio
    async def test_chat_completion_with_usage(self):
        provider = AzureOpenAIProvider(
            api_key="key", endpoint="https://test.openai.azure.com",
            api_version="2024-10-21", deployment="gpt-4o",
        )
        usage = SimpleNamespace(prompt_tokens=5, completion_tokens=15)
        fake_response = _make_chat_response(content="Hi", usage=usage)
        provider.client = MagicMock()
        provider.client.chat.completions.create = AsyncMock(return_value=fake_response)

        result = await provider.chat_completion(
            messages=[{"role": "user", "content": "test"}]
        )
        assert result.usage == {"prompt_tokens": 5, "completion_tokens": 15}

    @pytest.mark.asyncio
    async def test_parse_structured(self):
        provider = AzureOpenAIProvider(
            api_key="key", endpoint="https://test.openai.azure.com",
            api_version="2024-10-21", deployment="gpt-4o",
        )
        parsed_obj = {"title": "Azure Test"}
        msg = SimpleNamespace(parsed=parsed_obj)
        choice = SimpleNamespace(message=msg)
        fake_response = SimpleNamespace(choices=[choice])
        provider.client = MagicMock()
        provider.client.beta.chat.completions.parse = AsyncMock(return_value=fake_response)

        result = await provider.parse_structured(
            messages=[{"role": "user", "content": "test"}],
            response_format=dict,
        )
        assert result == parsed_obj
