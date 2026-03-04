"""Edge-case tests for ConversationService to cover remaining branches."""
import json
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient

from app.config import PromptConfig
from app.db.connection import mongodb
from app.db.registration_repo import RegistrationRepository
from app.db.session_repo import SessionRepository
from app.services.conversation import ConversationService
from app.services.duplicate_detector import DuplicateDetector
from app.services.llm.base import LLMResponse
from app.services.schema_extractor import ExtractedSchema, FieldDefinition, SchemaExtractor


@pytest_asyncio.fixture
async def db():
    client = AsyncMongoMockClient()
    mongodb.client = client
    mongodb.db = client["test_edge_cases"]
    yield mongodb.db
    client.close()


@pytest.fixture
def llm():
    provider = AsyncMock()
    provider.chat_completion.return_value = LLMResponse(
        content="Hello!", tool_calls=[], finish_reason="stop"
    )
    return provider


@pytest.fixture
def config(tmp_path):
    yaml_file = tmp_path / "prompt.yaml"
    yaml_file.write_text("""
system_prompt: |
  Collect car_type only.

expected_fields:
  - name: car_type
    type: string
    description: "Type of car"
""")
    return PromptConfig(str(yaml_file))


@pytest.fixture
def schema_no_pii():
    """Schema with NO PII fields — triggers early return in _check_duplicate."""
    return ExtractedSchema(
        title="Test",
        description="Test",
        fields=[
            FieldDefinition(name="car_type", type="string", description="Type of car"),
        ],
        pii_fields=[],
    )


@pytest.fixture
def schema_with_pii():
    return ExtractedSchema(
        title="Test",
        description="Test",
        fields=[
            FieldDefinition(name="car_type", type="string", description="Type of car"),
            FieldDefinition(
                name="customer_name", type="string", description="Name", pii=True
            ),
            FieldDefinition(
                name="birth_date", type="string", description="DOB", format="date", pii=True
            ),
        ],
        pii_fields=["customer_name", "birth_date"],
    )


@pytest_asyncio.fixture
async def svc_no_pii(db, llm, config, schema_no_pii):
    session_repo = SessionRepository()
    registration_repo = RegistrationRepository()
    extractor = SchemaExtractor(llm)
    extractor._cached_schema = schema_no_pii
    detector = DuplicateDetector(registration_repo)
    return ConversationService(
        llm=llm, schema_extractor=extractor, duplicate_detector=detector,
        session_repo=session_repo, registration_repo=registration_repo,
        prompt_config=config,
    )


@pytest_asyncio.fixture
async def svc_with_pii(db, llm, config, schema_with_pii):
    session_repo = SessionRepository()
    registration_repo = RegistrationRepository()
    extractor = SchemaExtractor(llm)
    extractor._cached_schema = schema_with_pii
    detector = DuplicateDetector(registration_repo)
    return ConversationService(
        llm=llm, schema_extractor=extractor, duplicate_detector=detector,
        session_repo=session_repo, registration_repo=registration_repo,
        prompt_config=config,
    )


class TestCheckDuplicateEdgeCases:
    @pytest.mark.asyncio
    async def test_no_pii_fields_skips_check(self, svc_no_pii):
        """When schema has no PII fields, _check_duplicate returns early (line 208)."""
        svc = svc_no_pii
        result = await svc.create_session()
        sid = result["session_id"]

        svc.llm.chat_completion.return_value = LLMResponse(
            content="Sedan noted!",
            tool_calls=[{
                "id": "call_1",
                "function": {
                    "name": "extract_customer_data",
                    "arguments": json.dumps({"car_type": "sedan"}),
                },
            }],
            finish_reason="stop",
        )
        response = await svc.process_message(sid, "sedan")
        assert response["status"] == "active"

    @pytest.mark.asyncio
    async def test_check_duplicate_session_gone_returns_early(self, svc_with_pii):
        """If session is deleted between extraction and _check_duplicate (line 213),
        _check_duplicate returns early without crashing."""
        svc = svc_with_pii

        # Directly call _check_duplicate with a nonexistent session
        schema = svc.schema_extractor._cached_schema
        # Should return None gracefully (session not found)
        await svc._check_duplicate(
            "nonexistent-session",
            {"customer_name": "Test", "birth_date": "2000-01-01"},
            schema,
        )


class TestFinalizeRegistrationEdgeCases:
    @pytest.mark.asyncio
    async def test_finalize_without_pii_fields(self, svc_no_pii):
        """Finalization without PII fields uses fallback hash (lines 247-248)."""
        svc = svc_no_pii
        result = await svc.create_session()
        sid = result["session_id"]

        # Extract a non-PII field
        svc.llm.chat_completion.return_value = LLMResponse(
            content="Sedan!",
            tool_calls=[{
                "id": "call_1",
                "function": {
                    "name": "extract_customer_data",
                    "arguments": json.dumps({"car_type": "sedan"}),
                },
            }],
            finish_reason="stop",
        )
        await svc.process_message(sid, "sedan")

        # Mark complete — finalize will run without PII fields
        svc.llm.chat_completion.return_value = LLMResponse(
            content="Done!",
            tool_calls=[{
                "id": "call_done",
                "function": {"name": "mark_registration_complete", "arguments": "{}"},
            }],
            finish_reason="stop",
        )
        response = await svc.process_message(sid, "confirm")
        assert response["status"] == "completed"

        # Registration should still be stored (with fallback hash)
        session = await svc.get_session(sid)
        assert session["status"] == "completed"

    @pytest.mark.asyncio
    async def test_finalize_with_session_deleted(self, svc_with_pii):
        """If session is deleted just before finalization (line 230)."""
        svc = svc_with_pii
        result = await svc.create_session()
        sid = result["session_id"]

        # Provide fields
        svc.llm.chat_completion.return_value = LLMResponse(
            content="Got it!",
            tool_calls=[{
                "id": "call_1",
                "function": {
                    "name": "extract_customer_data",
                    "arguments": json.dumps({
                        "car_type": "sedan",
                        "customer_name": "Test",
                        "birth_date": "2000-01-01",
                    }),
                },
            }],
            finish_reason="stop",
        )
        await svc.process_message(sid, "data")

        # Delete the session before finalize
        await svc.session_repo.delete(sid)

        # Now try to mark complete — session won't be found in _finalize
        svc.llm.chat_completion.return_value = LLMResponse(
            content="Done!",
            tool_calls=[{
                "id": "call_done",
                "function": {"name": "mark_registration_complete", "arguments": "{}"},
            }],
            finish_reason="stop",
        )
        # create a new session since the old one was deleted
        result2 = await svc.create_session()
        sid2 = result2["session_id"]
        # delete it right away
        await svc.session_repo.delete(sid2)

        # Call _finalize_registration directly with a nonexistent session
        await svc._finalize_registration("nonexistent-session-id")
        # Should not raise — just returns early
