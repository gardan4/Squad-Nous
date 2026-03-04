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
from app.services.llm.base import BaseLLMProvider, LLMResponse
from app.services.schema_extractor import ExtractedSchema, FieldDefinition, SchemaExtractor


@pytest_asyncio.fixture
async def db():
    client = AsyncMongoMockClient()
    mongodb.client = client
    mongodb.db = client["test_conversation_service"]
    yield mongodb.db
    client.close()


@pytest.fixture
def llm():
    provider = AsyncMock(spec=BaseLLMProvider)
    provider.chat_completion.return_value = LLMResponse(
        content="Hello! How can I help?", tool_calls=[], finish_reason="stop"
    )
    return provider


@pytest.fixture
def config(tmp_path):
    yaml_file = tmp_path / "prompt.yaml"
    yaml_file.write_text("""
system_prompt: |
  You are an AI Assistant for car insurance quotes.
  Collect: car_type, customer_name, birth_date.

expected_fields:
  - name: car_type
    type: string
    description: "Type of car"
  - name: customer_name
    type: string
    description: "Customer full name"
    pii: true
  - name: birth_date
    type: string
    format: date
    description: "Date of birth"
    pii: true
""")
    return PromptConfig(str(yaml_file))


@pytest.fixture
def schema():
    return ExtractedSchema(
        title="Car Insurance Quote",
        description="Collect car details.",
        fields=[
            FieldDefinition(name="car_type", type="string", description="Type of car"),
            FieldDefinition(
                name="customer_name", type="string", description="Customer full name", pii=True
            ),
            FieldDefinition(
                name="birth_date", type="string", description="Date of birth",
                format="date", pii=True,
            ),
        ],
        pii_fields=["customer_name", "birth_date"],
    )


@pytest_asyncio.fixture
async def svc(db, llm, config, schema):
    session_repo = SessionRepository()
    registration_repo = RegistrationRepository()
    extractor = SchemaExtractor(llm)
    extractor._cached_schema = schema
    detector = DuplicateDetector(registration_repo)
    service = ConversationService(
        llm=llm,
        schema_extractor=extractor,
        duplicate_detector=detector,
        session_repo=session_repo,
        registration_repo=registration_repo,
        prompt_config=config,
    )
    return service


class TestCreateSession:
    @pytest.mark.asyncio
    async def test_returns_session_id_and_active_status(self, svc):
        result = await svc.create_session()
        assert "session_id" in result
        assert result["status"] == "active"

    @pytest.mark.asyncio
    async def test_session_persisted_in_db(self, svc):
        result = await svc.create_session()
        session = await svc.get_session(result["session_id"])
        assert session is not None
        assert session["status"] == "active"
        assert session["messages"] == []
        assert session["extracted_fields"] == {}


class TestProcessMessage:
    @pytest.mark.asyncio
    async def test_raises_for_nonexistent_session(self, svc):
        with pytest.raises(ValueError, match="not found"):
            await svc.process_message("no-such-session", "hello")

    @pytest.mark.asyncio
    async def test_completed_session_returns_early(self, svc):
        result = await svc.create_session()
        sid = result["session_id"]
        await svc.session_repo.set_status(sid, "completed")

        response = await svc.process_message(sid, "hello again")
        assert response["status"] == "completed"
        assert "already been completed" in response["response"]
        # LLM should NOT have been called
        svc.llm.chat_completion.assert_not_called()

    @pytest.mark.asyncio
    async def test_llm_error_returns_graceful_fallback(self, svc):
        result = await svc.create_session()
        sid = result["session_id"]
        svc.llm.chat_completion.side_effect = RuntimeError("LLM is down")

        response = await svc.process_message(sid, "hello")
        assert response["status"] == "active"
        assert "temporary issue" in response["response"]

    @pytest.mark.asyncio
    async def test_stores_user_and_assistant_messages(self, svc):
        result = await svc.create_session()
        sid = result["session_id"]
        await svc.process_message(sid, "hello")

        session = await svc.get_session(sid)
        assert len(session["messages"]) == 2
        assert session["messages"][0]["role"] == "user"
        assert session["messages"][0]["content"] == "hello"
        assert session["messages"][1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_tool_call_extracts_fields(self, svc):
        result = await svc.create_session()
        sid = result["session_id"]
        svc.llm.chat_completion.return_value = LLMResponse(
            content="Great, a sedan!",
            tool_calls=[{
                "id": "call_1",
                "function": {
                    "name": "extract_customer_data",
                    "arguments": json.dumps({"car_type": "sedan"}),
                },
            }],
            finish_reason="stop",
        )

        response = await svc.process_message(sid, "It's a sedan")
        assert response["extracted_fields"]["car_type"] == "sedan"

    @pytest.mark.asyncio
    async def test_malformed_tool_call_json_handled(self, svc):
        """Invalid JSON in tool arguments should not crash the service."""
        result = await svc.create_session()
        sid = result["session_id"]
        svc.llm.chat_completion.return_value = LLMResponse(
            content="Let me note that.",
            tool_calls=[{
                "id": "call_bad",
                "function": {
                    "name": "extract_customer_data",
                    "arguments": "NOT VALID JSON{{{",
                },
            }],
            finish_reason="stop",
        )

        response = await svc.process_message(sid, "something")
        # Should not crash — returns normal response
        assert response["session_id"] == sid
        assert response["response"] == "Let me note that."

    @pytest.mark.asyncio
    async def test_empty_values_filtered_from_extraction(self, svc):
        """Tool call with empty-string values should not store them."""
        result = await svc.create_session()
        sid = result["session_id"]
        svc.llm.chat_completion.return_value = LLMResponse(
            content="Got it.",
            tool_calls=[{
                "id": "call_1",
                "function": {
                    "name": "extract_customer_data",
                    "arguments": json.dumps({"car_type": "sedan", "customer_name": ""}),
                },
            }],
            finish_reason="stop",
        )

        response = await svc.process_message(sid, "sedan")
        assert response["extracted_fields"]["car_type"] == "sedan"
        assert "customer_name" not in response["extracted_fields"]

    @pytest.mark.asyncio
    async def test_mark_registration_complete_finalizes(self, svc):
        """mark_registration_complete tool call should finalize the session."""
        result = await svc.create_session()
        sid = result["session_id"]

        # First provide PII fields so finalization can compute hash
        svc.llm.chat_completion.return_value = LLMResponse(
            content="Thanks!",
            tool_calls=[{
                "id": "call_1",
                "function": {
                    "name": "extract_customer_data",
                    "arguments": json.dumps({
                        "customer_name": "Test User",
                        "birth_date": "2000-01-01",
                        "car_type": "sedan",
                    }),
                },
            }],
            finish_reason="stop",
        )
        await svc.process_message(sid, "Test User, born 2000-01-01, sedan")

        # Now complete
        svc.llm.chat_completion.return_value = LLMResponse(
            content="Registration complete!",
            tool_calls=[{
                "id": "call_done",
                "function": {"name": "mark_registration_complete", "arguments": "{}"},
            }],
            finish_reason="stop",
        )
        response = await svc.process_message(sid, "Yes, confirm")
        assert response["status"] == "completed"

        # Verify registration exists in DB
        sv = svc.prompt_config.schema_version
        pii_hash = DuplicateDetector.compute_pii_hash("Test User", "2000-01-01", sv)
        reg = await svc.registration_repo.find_by_pii_hash(pii_hash)
        assert reg is not None
        assert reg["fields"]["car_type"] == "sedan"

    @pytest.mark.asyncio
    async def test_followup_call_when_no_text_response(self, svc):
        """When LLM returns tool calls but no text, a follow-up call is made."""
        result = await svc.create_session()
        sid = result["session_id"]

        # First call: tool call with empty content
        first_response = LLMResponse(
            content="",
            tool_calls=[{
                "id": "call_1",
                "function": {
                    "name": "extract_customer_data",
                    "arguments": json.dumps({"car_type": "sedan"}),
                },
            }],
            finish_reason="stop",
        )
        # Follow-up call: text response
        followup_response = LLMResponse(
            content="Great, a sedan! What's the manufacturer?",
            tool_calls=[],
            finish_reason="stop",
        )
        svc.llm.chat_completion.side_effect = [first_response, followup_response]

        response = await svc.process_message(sid, "sedan")
        assert response["response"] == "Great, a sedan! What's the manufacturer?"
        assert svc.llm.chat_completion.call_count == 2

    @pytest.mark.asyncio
    async def test_followup_call_failure_uses_fallback_text(self, svc):
        """If the follow-up LLM call fails, use a default fallback message."""
        result = await svc.create_session()
        sid = result["session_id"]

        first_response = LLMResponse(
            content="",
            tool_calls=[{
                "id": "call_1",
                "function": {
                    "name": "extract_customer_data",
                    "arguments": json.dumps({"car_type": "sedan"}),
                },
            }],
            finish_reason="stop",
        )
        svc.llm.chat_completion.side_effect = [first_response, RuntimeError("LLM down")]

        response = await svc.process_message(sid, "sedan")
        # Should use the hardcoded fallback
        fallback = response["response"].lower()
        assert "next question" in fallback or "continue" in fallback
        assert response["extracted_fields"]["car_type"] == "sedan"


class TestCheckDuplicate:
    @pytest.mark.asyncio
    async def test_no_check_without_both_pii_fields(self, svc):
        """Duplicate check should not run if only name (no DOB) is provided."""
        result = await svc.create_session()
        sid = result["session_id"]
        svc.llm.chat_completion.return_value = LLMResponse(
            content="Thanks! When were you born?",
            tool_calls=[{
                "id": "call_1",
                "function": {
                    "name": "extract_customer_data",
                    "arguments": json.dumps({"customer_name": "Jan de Vries"}),
                },
            }],
            finish_reason="stop",
        )
        response = await svc.process_message(sid, "Jan de Vries")
        # Status should remain active (no duplicate check with partial PII)
        assert response["status"] == "active"

    @pytest.mark.asyncio
    async def test_duplicate_detected_when_both_pii_match(self, svc):
        """Providing matching name+DOB against existing registration triggers duplicate."""
        sv = svc.prompt_config.schema_version
        pii_hash = DuplicateDetector.compute_pii_hash("Jan de Vries", "1985-06-15", sv)
        await svc.registration_repo.create(pii_hash, {"car_type": "sedan"}, sv)

        result = await svc.create_session()
        sid = result["session_id"]

        # Provide name
        svc.llm.chat_completion.return_value = LLMResponse(
            content="Thanks!",
            tool_calls=[{
                "id": "call_1",
                "function": {
                    "name": "extract_customer_data",
                    "arguments": json.dumps({"customer_name": "Jan de Vries"}),
                },
            }],
            finish_reason="stop",
        )
        await svc.process_message(sid, "Jan de Vries")

        # Provide DOB → triggers duplicate
        svc.llm.chat_completion.return_value = LLMResponse(
            content="Hmm, I see a match.",
            tool_calls=[{
                "id": "call_2",
                "function": {
                    "name": "extract_customer_data",
                    "arguments": json.dumps({"birth_date": "1985-06-15"}),
                },
            }],
            finish_reason="stop",
        )
        await svc.process_message(sid, "June 15 1985")
        session = await svc.get_session(sid)
        assert session["status"] == "duplicate_detected"


class TestCloseSession:
    @pytest.mark.asyncio
    async def test_close_sets_abandoned(self, svc):
        result = await svc.create_session()
        sid = result["session_id"]
        await svc.close_session(sid)
        session = await svc.get_session(sid)
        assert session["status"] == "abandoned"

    @pytest.mark.asyncio
    async def test_close_nonexistent_does_not_crash(self, svc):
        # Should not raise
        await svc.close_session("no-such-session")


class TestGetSession:
    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent(self, svc):
        result = await svc.get_session("no-such-session")
        assert result is None
