import pytest


@pytest.mark.asyncio
async def test_list_sessions_empty(test_client):
    response = await test_client.get("/api/admin/sessions")
    assert response.status_code == 200
    data = response.json()
    assert data["sessions"] == [] or isinstance(data["sessions"], list)
    assert "count" in data


@pytest.mark.asyncio
async def test_list_sessions_with_data(test_client):
    # Create a session
    await test_client.post("/api/session")
    response = await test_client.get("/api/admin/sessions")
    data = response.json()
    assert data["count"] >= 1
    assert len(data["sessions"]) >= 1


@pytest.mark.asyncio
async def test_list_sessions_filter_by_status(test_client):
    await test_client.post("/api/session")
    response = await test_client.get("/api/admin/sessions?status=active")
    data = response.json()
    for s in data["sessions"]:
        assert s["status"] == "active"


@pytest.mark.asyncio
async def test_list_sessions_with_limit(test_client):
    await test_client.post("/api/session")
    await test_client.post("/api/session")
    response = await test_client.get("/api/admin/sessions?limit=1")
    data = response.json()
    assert len(data["sessions"]) <= 1


@pytest.mark.asyncio
async def test_list_registrations_empty(test_client):
    response = await test_client.get("/api/admin/registrations")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["registrations"], list)
    assert "count" in data


@pytest.mark.asyncio
async def test_list_registrations_with_data(test_client, services):
    reg_repo = services["registration_repo"]
    await reg_repo.create("hash123", {"car_type": "sedan"}, "v1")

    response = await test_client.get("/api/admin/registrations")
    data = response.json()
    assert data["count"] >= 1


@pytest.mark.asyncio
async def test_get_stats(test_client):
    await test_client.post("/api/session")
    response = await test_client.get("/api/admin/stats")
    assert response.status_code == 200
    data = response.json()
    assert "sessions" in data
    assert "total" in data["sessions"]
    assert "active" in data["sessions"]
    assert "completed" in data["sessions"]
    assert "registrations" in data


@pytest.mark.asyncio
async def test_clear_sessions(test_client):
    await test_client.post("/api/session")
    response = await test_client.delete("/api/admin/sessions")
    assert response.status_code == 200
    assert response.json()["deleted"] >= 1

    # Verify sessions are gone
    list_resp = await test_client.get("/api/admin/sessions")
    assert list_resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_clear_registrations(test_client, services):
    reg_repo = services["registration_repo"]
    await reg_repo.create("hash456", {"car_type": "coupe"}, "v1")

    response = await test_client.delete("/api/admin/registrations")
    assert response.status_code == 200
    assert response.json()["deleted"] >= 1
