import json

import pytest

from app.services.llm.base import LLMResponse


def make_llm_response(content: str, tool_calls: list | None = None) -> LLMResponse:
    """Helper to create LLM responses."""
    return LLMResponse(
        content=content,
        tool_calls=tool_calls or [],
        finish_reason="stop",
    )


def make_tool_call(fields: dict) -> list[dict]:
    """Helper to create tool call data."""
    return [{
        "id": "call_1",
        "function": {
            "name": "extract_customer_data",
            "arguments": json.dumps(fields),
        },
    }]


@pytest.mark.asyncio
async def test_full_conversation_flow(test_client, services):
    """Test a complete conversation from start to registration completion."""
    mock_llm = services["llm"]

    # Step 1: Create session
    resp = await test_client.post("/api/session")
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    # Step 2: User greets — LLM asks for car type
    mock_llm.chat_completion.return_value = make_llm_response(
        "Hello! I'd love to help with your car insurance quote. What type of car do you have? "
        "We cover sedans, coupes, station wagons, hatchbacks, and minivans."
    )
    resp = await test_client.post(
        "/api/chat", json={"session_id": session_id, "message": "Hi there"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"

    # Step 3: User provides car type — LLM extracts it and asks for manufacturer
    mock_llm.chat_completion.return_value = make_llm_response(
        "A sedan, great choice! And what is the manufacturer of your car?",
        tool_calls=make_tool_call({"car_type": "sedan"}),
    )
    resp = await test_client.post(
        "/api/chat", json={"session_id": session_id, "message": "It's a sedan"}
    )
    assert resp.status_code == 200
    assert resp.json()["extracted_fields"].get("car_type") == "sedan"

    # Step 4: Manufacturer
    mock_llm.chat_completion.return_value = make_llm_response(
        "Toyota — excellent! What year was your car manufactured?",
        tool_calls=make_tool_call({"manufacturer": "Toyota"}),
    )
    resp = await test_client.post(
        "/api/chat", json={"session_id": session_id, "message": "Toyota"}
    )
    assert resp.json()["extracted_fields"].get("manufacturer") == "Toyota"

    # Step 5: Year of construction
    mock_llm.chat_completion.return_value = make_llm_response(
        "2020 model. And what is your license plate number?",
        tool_calls=make_tool_call({"year_of_construction": 2020}),
    )
    resp = await test_client.post(
        "/api/chat", json={"session_id": session_id, "message": "2020"}
    )
    assert resp.json()["extracted_fields"].get("year_of_construction") == 2020

    # Step 6: License plate
    mock_llm.chat_completion.return_value = make_llm_response(
        "Thank you! Now, could you please tell me your full name?",
        tool_calls=make_tool_call({"license_plate": "AB-123-CD"}),
    )
    resp = await test_client.post(
        "/api/chat", json={"session_id": session_id, "message": "AB-123-CD"}
    )
    assert resp.json()["extracted_fields"].get("license_plate") == "AB-123-CD"

    # Step 7: Customer name
    mock_llm.chat_completion.return_value = make_llm_response(
        "Thank you, Jan de Vries! And what is your date of birth?",
        tool_calls=make_tool_call({"customer_name": "Jan de Vries"}),
    )
    resp = await test_client.post(
        "/api/chat", json={"session_id": session_id, "message": "Jan de Vries"}
    )
    assert resp.json()["extracted_fields"].get("customer_name") == "Jan de Vries"

    # Step 8: Birth date
    mock_llm.chat_completion.return_value = make_llm_response(
        "Let me confirm your details:\n"
        "- Car type: Sedan\n"
        "- Manufacturer: Toyota\n"
        "- Year: 2020\n"
        "- License plate: AB-123-CD\n"
        "- Name: Jan de Vries\n"
        "- Date of birth: 1985-06-15\n\n"
        "Is everything correct?",
        tool_calls=make_tool_call({"birth_date": "1985-06-15"}),
    )
    resp = await test_client.post(
        "/api/chat", json={"session_id": session_id, "message": "June 15, 1985"}
    )
    assert resp.json()["extracted_fields"].get("birth_date") == "1985-06-15"

    # Step 9: User confirms — LLM calls mark_registration_complete
    mock_llm.chat_completion.return_value = make_llm_response(
        "Thank you, Jan! Your car insurance quote registration is now complete. "
        "Our quoting department will process your request shortly.",
        tool_calls=[{
            "id": "call_done",
            "function": {
                "name": "mark_registration_complete",
                "arguments": "{}",
            },
        }],
    )
    resp = await test_client.post(
        "/api/chat", json={"session_id": session_id, "message": "Yes, that's all correct"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    # Step 10: Verify session is completed
    resp = await test_client.get(f"/api/session/{session_id}")
    assert resp.json()["status"] == "completed"

    # Step 11: Verify registration was stored in database
    reg_repo = services["registration_repo"]
    from app.services.duplicate_detector import DuplicateDetector
    sv = services["prompt_config"].schema_version
    pii_hash = DuplicateDetector.compute_pii_hash("Jan de Vries", "1985-06-15", sv)
    registration = await reg_repo.find_by_pii_hash(pii_hash)
    assert registration is not None
    assert registration["fields"]["car_type"] == "sedan"
    assert registration["fields"]["manufacturer"] == "Toyota"


@pytest.mark.asyncio
async def test_duplicate_detection_flow(test_client, services):
    """Test that registering the same person twice triggers duplicate detection."""
    mock_llm = services["llm"]
    reg_repo = services["registration_repo"]

    # Pre-create an existing registration with the same schema_version
    from app.services.duplicate_detector import DuplicateDetector
    sv = services["prompt_config"].schema_version
    pii_hash = DuplicateDetector.compute_pii_hash("Jan de Vries", "1985-06-15", sv)
    await reg_repo.create(
        pii_hash=pii_hash,
        fields={"car_type": "sedan", "customer_name": "Jan de Vries", "birth_date": "1985-06-15"},
        schema_version=sv,
    )

    # Create session and provide PII that matches
    resp = await test_client.post("/api/session")
    session_id = resp.json()["session_id"]

    # Provide name and birthdate that trigger duplicate check
    mock_llm.chat_completion.return_value = make_llm_response(
        "Thank you! And what is your date of birth?",
        tool_calls=make_tool_call({"customer_name": "Jan de Vries"}),
    )
    await test_client.post(
        "/api/chat", json={"session_id": session_id, "message": "Jan de Vries"}
    )

    mock_llm.chat_completion.return_value = make_llm_response(
        "I notice we may already have a registration on file for you. "
        "Would you like to update your existing details?",
        tool_calls=make_tool_call({"birth_date": "1985-06-15"}),
    )
    resp = await test_client.post(
        "/api/chat", json={"session_id": session_id, "message": "June 15, 1985"}
    )

    # Session should be marked as duplicate_detected
    session_resp = await test_client.get(f"/api/session/{session_id}")
    assert session_resp.json()["status"] == "duplicate_detected"


@pytest.mark.asyncio
async def test_field_correction_overwrites_previous_value(test_client, services):
    """When the user corrects a previously extracted field, the new value should overwrite."""
    mock_llm = services["llm"]

    resp = await test_client.post("/api/session")
    session_id = resp.json()["session_id"]

    # First: extract car_type as "sedan"
    mock_llm.chat_completion.return_value = make_llm_response(
        "A sedan, got it!",
        tool_calls=make_tool_call({"car_type": "sedan"}),
    )
    resp = await test_client.post(
        "/api/chat", json={"session_id": session_id, "message": "It's a sedan"}
    )
    assert resp.json()["extracted_fields"]["car_type"] == "sedan"

    # Second: user corrects to "hatchback"
    mock_llm.chat_completion.return_value = make_llm_response(
        "No problem, I'll update that to hatchback.",
        tool_calls=make_tool_call({"car_type": "hatchback"}),
    )
    resp = await test_client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "Actually, it's a hatchback"},
    )
    assert resp.json()["extracted_fields"]["car_type"] == "hatchback"

    # Verify via GET session
    session_resp = await test_client.get(f"/api/session/{session_id}")
    assert session_resp.json()["extracted_fields"]["car_type"] == "hatchback"


@pytest.mark.asyncio
async def test_multiple_fields_extracted_in_single_message(test_client, services):
    """LLM can extract multiple fields from a single user message."""
    mock_llm = services["llm"]

    resp = await test_client.post("/api/session")
    session_id = resp.json()["session_id"]

    # User provides multiple pieces of info at once
    mock_llm.chat_completion.return_value = make_llm_response(
        "Thank you! I've noted your sedan Toyota from 2020.",
        tool_calls=make_tool_call({
            "car_type": "sedan",
            "manufacturer": "Toyota",
            "year_of_construction": 2020,
        }),
    )
    resp = await test_client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "I have a 2020 Toyota sedan"},
    )
    fields = resp.json()["extracted_fields"]
    assert fields["car_type"] == "sedan"
    assert fields["manufacturer"] == "Toyota"
    assert fields["year_of_construction"] == 2020


@pytest.mark.asyncio
async def test_message_to_completed_session(test_client, services):
    """Sending a message to a completed session returns a completed-status response."""
    mock_llm = services["llm"]

    resp = await test_client.post("/api/session")
    session_id = resp.json()["session_id"]

    # Provide all fields at once
    mock_llm.chat_completion.return_value = make_llm_response(
        "Got all your details!",
        tool_calls=make_tool_call({
            "car_type": "sedan",
            "manufacturer": "Toyota",
            "year_of_construction": 2020,
            "license_plate": "AB-123-CD",
            "customer_name": "Test User",
            "birth_date": "2000-01-01",
        }),
    )
    await test_client.post(
        "/api/chat", json={"session_id": session_id, "message": "All my details"}
    )

    # Mark complete
    mock_llm.chat_completion.return_value = make_llm_response(
        "All done!",
        tool_calls=[{
            "id": "call_done",
            "function": {"name": "mark_registration_complete", "arguments": "{}"},
        }],
    )
    resp = await test_client.post(
        "/api/chat", json={"session_id": session_id, "message": "Yes, confirm"}
    )
    assert resp.json()["status"] == "completed"

    # Now try to send another message
    mock_llm.chat_completion.return_value = make_llm_response("Hello!", tool_calls=[])
    resp = await test_client.post(
        "/api/chat", json={"session_id": session_id, "message": "Hello again"}
    )
    assert resp.json()["status"] == "completed"
    assert "already been completed" in resp.json()["response"]


@pytest.mark.asyncio
async def test_partial_conversation_then_close(test_client, services):
    """User can abandon a session mid-conversation; fields collected so far are preserved."""
    mock_llm = services["llm"]

    resp = await test_client.post("/api/session")
    session_id = resp.json()["session_id"]

    # Extract one field
    mock_llm.chat_completion.return_value = make_llm_response(
        "Sedan noted! What's the manufacturer?",
        tool_calls=make_tool_call({"car_type": "sedan"}),
    )
    await test_client.post(
        "/api/chat", json={"session_id": session_id, "message": "It's a sedan"}
    )

    # Close the session mid-conversation
    resp = await test_client.delete(f"/api/session/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"

    # Verify session is abandoned but fields are preserved
    session_resp = await test_client.get(f"/api/session/{session_id}")
    data = session_resp.json()
    assert data["status"] == "abandoned"
    assert data["extracted_fields"]["car_type"] == "sedan"


@pytest.mark.asyncio
async def test_duplicate_then_complete_updates_existing_registration(test_client, services):
    """When a duplicate is detected and the user completes again, the registration is updated."""
    mock_llm = services["llm"]
    reg_repo = services["registration_repo"]
    from app.services.duplicate_detector import DuplicateDetector

    sv = services["prompt_config"].schema_version

    # Pre-create existing registration
    pii_hash = DuplicateDetector.compute_pii_hash("Jan de Vries", "1985-06-15", sv)
    await reg_repo.create(
        pii_hash=pii_hash,
        fields={
            "car_type": "sedan",
            "manufacturer": "Toyota",
            "customer_name": "Jan de Vries",
            "birth_date": "1985-06-15",
        },
        schema_version=sv,
    )

    # Create session and trigger duplicate
    resp = await test_client.post("/api/session")
    session_id = resp.json()["session_id"]

    mock_llm.chat_completion.return_value = make_llm_response(
        "Thanks!",
        tool_calls=make_tool_call({"customer_name": "Jan de Vries"}),
    )
    await test_client.post(
        "/api/chat", json={"session_id": session_id, "message": "Jan de Vries"}
    )

    mock_llm.chat_completion.return_value = make_llm_response(
        "I see you've registered before. Would you like to update?",
        tool_calls=make_tool_call({"birth_date": "1985-06-15"}),
    )
    await test_client.post(
        "/api/chat", json={"session_id": session_id, "message": "1985-06-15"}
    )

    # Verify duplicate detected
    session_resp = await test_client.get(f"/api/session/{session_id}")
    assert session_resp.json()["status"] == "duplicate_detected"

    # User provides updated car info
    mock_llm.chat_completion.return_value = make_llm_response(
        "Updated to Honda!",
        tool_calls=make_tool_call({
            "car_type": "hatchback",
            "manufacturer": "Honda",
            "year_of_construction": 2023,
            "license_plate": "XY-999-ZZ",
        }),
    )
    await test_client.post(
        "/api/chat", json={"session_id": session_id, "message": "Honda hatchback 2023 XY-999-ZZ"}
    )

    # Complete the registration
    mock_llm.chat_completion.return_value = make_llm_response(
        "Updated your registration!",
        tool_calls=[{
            "id": "call_done",
            "function": {"name": "mark_registration_complete", "arguments": "{}"},
        }],
    )
    resp = await test_client.post(
        "/api/chat", json={"session_id": session_id, "message": "Yes, update it"}
    )
    assert resp.json()["status"] == "completed"

    # Verify the registration was updated (not duplicated)
    reg = await reg_repo.find_by_pii_hash(pii_hash)
    assert reg is not None
    assert reg["fields"]["manufacturer"] == "Honda"
    assert reg["fields"]["car_type"] == "hatchback"
    # History should have the previous version
    assert len(reg["history"]) == 1
    assert reg["history"][0]["fields"]["manufacturer"] == "Toyota"
