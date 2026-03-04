from datetime import UTC, datetime
from typing import Any

from app.db.connection import mongodb


class SessionRepository:
    @property
    def collection(self):
        return mongodb.db["sessions"]

    async def create(self, session_id: str, schema_version: str) -> dict:
        doc = {
            "session_id": session_id,
            "status": "active",
            "messages": [],
            "extracted_fields": {},
            "schema_version": schema_version,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        await self.collection.insert_one(doc)
        return doc

    async def get(self, session_id: str) -> dict | None:
        return await self.collection.find_one({"session_id": session_id}, {"_id": 0})

    async def append_message(self, session_id: str, role: str, content: str):
        await self.collection.update_one(
            {"session_id": session_id},
            {
                "$push": {
                    "messages": {
                        "role": role,
                        "content": content,
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                },
                "$set": {"updated_at": datetime.now(UTC)},
            },
        )

    async def update_fields(self, session_id: str, fields: dict[str, Any]):
        set_ops = {f"extracted_fields.{k}": v for k, v in fields.items()}
        set_ops["updated_at"] = datetime.now(UTC)
        await self.collection.update_one(
            {"session_id": session_id},
            {"$set": set_ops},
        )

    async def set_status(self, session_id: str, status: str):
        await self.collection.update_one(
            {"session_id": session_id},
            {"$set": {"status": status, "updated_at": datetime.now(UTC)}},
        )

    async def delete(self, session_id: str):
        await self.collection.delete_one({"session_id": session_id})
