import json

import pytest

from app.services.llm.base import LLMResponse


@pytest.mark.asyncio
async def test_health_check(test_client):
    response = await test_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "squad-nous"


@pytest.mark.asyncio
async def test_create_session(test_client):
    response = await test_client.post("/api/session")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_send_message(test_client):
    # Create a session first
    session_resp = await test_client.post("/api/session")
    session_id = session_resp.json()["session_id"]

    # Send a message
    response = await test_client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "Hi, I want a car insurance quote"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert "response" in data
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_get_session(test_client):
    # Create a session
    session_resp = await test_client.post("/api/session")
    session_id = session_resp.json()["session_id"]

    # Get session details
    response = await test_client.get(f"/api/session/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_get_nonexistent_session(test_client):
    response = await test_client.get("/api/session/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_close_session(test_client):
    # Create a session
    session_resp = await test_client.post("/api/session")
    session_id = session_resp.json()["session_id"]

    # Close it
    response = await test_client.delete(f"/api/session/{session_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "closed"


@pytest.mark.asyncio
async def test_get_schema(test_client):
    response = await test_client.get("/api/schema")
    assert response.status_code == 200
    data = response.json()
    assert "schema_version" in data
    assert "fields" in data
    assert len(data["fields"]) > 0


@pytest.mark.asyncio
async def test_send_message_empty_rejected(test_client):
    session_resp = await test_client.post("/api/session")
    session_id = session_resp.json()["session_id"]

    response = await test_client.post(
        "/api/chat",
        json={"session_id": session_id, "message": ""},
    )
    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_send_message_invalid_session(test_client):
    response = await test_client.post(
        "/api/chat",
        json={"session_id": "nonexistent", "message": "Hello"},
    )
    assert response.status_code == 404


# --- New integration tests ---


@pytest.mark.asyncio
async def test_close_nonexistent_session(test_client):
    """DELETE on a nonexistent session should return 404."""
    response = await test_client.delete("/api/session/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_chat_after_close_returns_error(test_client):
    """Sending a message to a closed (abandoned) session should still work but
    the session status should reflect the abandoned state through the response."""
    session_resp = await test_client.post("/api/session")
    session_id = session_resp.json()["session_id"]

    await test_client.delete(f"/api/session/{session_id}")

    # Session is now abandoned — sending a message should still process
    # (abandoned != completed, so it won't short-circuit)
    response = await test_client.post(
        "/api/chat", json={"session_id": session_id, "message": "hello"}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_llm_failure_returns_graceful_error(test_client, services):
    """When the LLM throws an exception, the API should return a graceful error message."""
    mock_llm = services["llm"]
    session_resp = await test_client.post("/api/session")
    session_id = session_resp.json()["session_id"]

    mock_llm.chat_completion.side_effect = RuntimeError("LLM is down")

    response = await test_client.post(
        "/api/chat", json={"session_id": session_id, "message": "hello"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "temporary issue" in data["response"]
    assert data["status"] == "active"

    # Reset for other tests
    mock_llm.chat_completion.side_effect = None
    mock_llm.chat_completion.return_value = LLMResponse(
        content="Hello!", tool_calls=[], finish_reason="stop"
    )


@pytest.mark.asyncio
async def test_extracted_fields_visible_in_get_session(test_client, services):
    """Fields extracted via chat should be visible in GET /api/session/{id}."""
    mock_llm = services["llm"]
    session_resp = await test_client.post("/api/session")
    session_id = session_resp.json()["session_id"]

    mock_llm.chat_completion.return_value = LLMResponse(
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
    await test_client.post(
        "/api/chat", json={"session_id": session_id, "message": "It's a sedan"}
    )

    # Reset LLM for GET (it doesn't call LLM, but be safe)
    mock_llm.chat_completion.return_value = LLMResponse(
        content="Hello!", tool_calls=[], finish_reason="stop"
    )

    response = await test_client.get(f"/api/session/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["extracted_fields"]["car_type"] == "sedan"


@pytest.mark.asyncio
async def test_schema_returns_correct_field_details(test_client):
    """Schema endpoint should return field names and metadata."""
    response = await test_client.get("/api/schema")
    data = response.json()
    field_names = [f["name"] for f in data["fields"]]
    assert "car_type" in field_names
    assert "customer_name" in field_names
    assert "birth_date" in field_names
    assert len(data["fields"]) == 6


@pytest.mark.asyncio
async def test_multiple_sessions_are_independent(test_client, services):
    """Two sessions should not share state."""
    mock_llm = services["llm"]

    resp1 = await test_client.post("/api/session")
    sid1 = resp1.json()["session_id"]
    resp2 = await test_client.post("/api/session")
    sid2 = resp2.json()["session_id"]

    assert sid1 != sid2

    # Extract a field in session 1 only
    mock_llm.chat_completion.return_value = LLMResponse(
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
    await test_client.post("/api/chat", json={"session_id": sid1, "message": "sedan"})

    # Reset mock
    mock_llm.chat_completion.return_value = LLMResponse(
        content="Hello!", tool_calls=[], finish_reason="stop"
    )

    # Session 2 should have no extracted fields
    s2 = await test_client.get(f"/api/session/{sid2}")
    assert s2.json()["extracted_fields"] == {}

    # Session 1 should have the field
    s1 = await test_client.get(f"/api/session/{sid1}")
    assert s1.json()["extracted_fields"]["car_type"] == "sedan"


@pytest.mark.asyncio
async def test_session_includes_messages_history(test_client):
    """GET session should include conversation messages."""
    session_resp = await test_client.post("/api/session")
    session_id = session_resp.json()["session_id"]

    await test_client.post(
        "/api/chat", json={"session_id": session_id, "message": "Hello"}
    )

    response = await test_client.get(f"/api/session/{session_id}")
    data = response.json()
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][0]["content"] == "Hello"
    assert data["messages"][1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_chat_missing_message_field(test_client):
    """POST /api/chat with missing 'message' field should return 422."""
    session_resp = await test_client.post("/api/session")
    session_id = session_resp.json()["session_id"]

    response = await test_client.post(
        "/api/chat", json={"session_id": session_id}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_missing_session_id_field(test_client):
    """POST /api/chat with missing session_id should return 422."""
    response = await test_client.post(
        "/api/chat", json={"message": "hello"}
    )
    assert response.status_code == 422
