"""Tests for app startup lifespan and global exception handler."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.services.schema_extractor import ExtractedSchema


@pytest.mark.asyncio
async def test_lifespan_startup_and_shutdown():
    """Test that the lifespan context manager starts and shuts down correctly."""
    with (
        patch("app.main.mongodb") as mock_mongodb,
        patch("app.main.create_llm_provider") as mock_factory,
        patch("app.main.PromptConfig") as mock_prompt_cls,
        patch("app.main.get_settings") as mock_settings_fn,
    ):
        # Configure mocks
        settings = MagicMock()
        settings.mongodb_url = "mongodb://localhost:27017"
        settings.mongodb_database = "test"
        settings.session_ttl_seconds = 3600
        settings.llm_provider = "azure_openai"
        settings.prompt_config_path = "config/prompt.yaml"
        mock_settings_fn.return_value = settings

        mock_mongodb.connect = AsyncMock()
        mock_mongodb.close = AsyncMock()

        mock_llm = AsyncMock()
        mock_factory.return_value = mock_llm

        mock_config = MagicMock()
        mock_config.schema_version = "abc123"
        mock_config.system_prompt = "Test"
        mock_prompt_cls.return_value = mock_config

        # Mock schema extraction
        mock_llm.parse_structured.return_value = ExtractedSchema(
            title="Test", description="Test", fields=[], pii_fields=[]
        )

        from app.main import app, lifespan

        async with lifespan(app):
            mock_mongodb.connect.assert_called_once()
            mock_factory.assert_called_once_with(settings)

        mock_mongodb.close.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_schema_extraction_failure():
    """If schema extraction fails at startup, the app should still start."""
    with (
        patch("app.main.mongodb") as mock_mongodb,
        patch("app.main.create_llm_provider") as mock_factory,
        patch("app.main.PromptConfig") as mock_prompt_cls,
        patch("app.main.get_settings") as mock_settings_fn,
    ):
        settings = MagicMock()
        settings.mongodb_url = "mongodb://localhost:27017"
        settings.mongodb_database = "test"
        settings.session_ttl_seconds = 3600
        settings.llm_provider = "azure_openai"
        settings.prompt_config_path = "config/prompt.yaml"
        mock_settings_fn.return_value = settings

        mock_mongodb.connect = AsyncMock()
        mock_mongodb.close = AsyncMock()

        mock_llm = AsyncMock()
        mock_factory.return_value = mock_llm

        mock_config = MagicMock()
        mock_config.schema_version = "abc123"
        mock_config.system_prompt = "Test"
        mock_prompt_cls.return_value = mock_config

        # Schema extraction fails
        mock_llm.parse_structured.side_effect = RuntimeError("LLM down")

        from app.main import app, lifespan

        # Should not raise despite schema extraction failure
        async with lifespan(app):
            pass

        mock_mongodb.close.assert_called_once()


@pytest.mark.asyncio
async def test_global_exception_handler(services):
    """Unhandled exceptions should return a 500 with generic message."""
    from app.main import app

    # Force an unhandled exception by making the conversation service raise
    original = services["conversation"].process_message
    services["conversation"].process_message = AsyncMock(
        side_effect=RuntimeError("Unexpected boom")
    )

    # Need raise_app_exceptions=False so httpx returns the 500 instead of raising
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/session")
        session_id = resp.json()["session_id"]

        resp = await client.post(
            "/api/chat", json={"session_id": session_id, "message": "hello"}
        )
        assert resp.status_code == 500
        assert "internal error" in resp.json()["detail"].lower()

    services["conversation"].process_message = original
