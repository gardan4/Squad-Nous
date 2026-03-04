from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient

from app.db.connection import MongoDB, mongodb
from app.db.registration_repo import RegistrationRepository
from app.db.session_repo import SessionRepository


class TestMongoDB:
    @pytest.mark.asyncio
    async def test_connect_creates_indexes(self):
        db = MongoDB()
        await db.connect("mongodb://localhost:27017", "test_connect_db")
        assert db.db is not None
        await db.close()

    @pytest.mark.asyncio
    async def test_close_when_no_client(self):
        db = MongoDB()
        db.client = None
        await db.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_ping_returns_false_when_no_client(self):
        db = MongoDB()
        db.client = None
        assert await db.ping() is False

    @pytest.mark.asyncio
    async def test_ping_returns_false_on_error(self):
        db = MongoDB()
        db.client = MagicMock()
        db.client.admin.command = AsyncMock(side_effect=ConnectionError("no connection"))
        assert await db.ping() is False

    @pytest.mark.asyncio
    async def test_ping_returns_true_on_success(self):
        db = MongoDB()
        db.client = MagicMock()
        db.client.admin.command = AsyncMock(return_value={"ok": 1})
        assert await db.ping() is True


class TestSessionRepository:
    @pytest_asyncio.fixture
    async def repo(self):
        client = AsyncMongoMockClient()
        mongodb.client = client
        mongodb.db = client["test_session_repo"]
        yield SessionRepository()
        client.close()

    @pytest.mark.asyncio
    async def test_delete_removes_session(self, repo):
        await repo.create("sess-1", "v1")
        await repo.delete("sess-1")
        assert await repo.get("sess-1") is None


class TestRegistrationRepository:
    @pytest_asyncio.fixture
    async def repo(self):
        client = AsyncMongoMockClient()
        mongodb.client = client
        mongodb.db = client["test_reg_repo"]
        yield RegistrationRepository()
        client.close()

    @pytest.mark.asyncio
    async def test_update_with_history_creates_when_not_found(self, repo):
        """update_with_history should create a new registration if none exists."""
        await repo.update_with_history("new_hash", {"car_type": "coupe"}, "v1")
        reg = await repo.find_by_pii_hash("new_hash")
        assert reg is not None
        assert reg["fields"]["car_type"] == "coupe"
        assert reg["history"] == []
