from datetime import UTC, datetime
from typing import Any

from app.db.connection import mongodb


class RegistrationRepository:
    @property
    def collection(self):
        return mongodb.db["registrations"]

    async def find_by_pii_hash(self, pii_hash: str) -> dict | None:
        return await self.collection.find_one({"pii_hash": pii_hash}, {"_id": 0})

    async def create(self, pii_hash: str, fields: dict[str, Any], schema_version: str) -> dict:
        doc = {
            "pii_hash": pii_hash,
            "fields": fields,
            "schema_version": schema_version,
            "history": [],
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        await self.collection.insert_one(doc)
        return doc

    async def update_with_history(
        self, pii_hash: str, fields: dict[str, Any], schema_version: str
    ):
        """Update registration, archiving the previous version in history."""
        existing = await self.find_by_pii_hash(pii_hash)
        if not existing:
            return await self.create(pii_hash, fields, schema_version)

        history_entry = {
            "fields": existing.get("fields", {}),
            "schema_version": existing.get("schema_version", ""),
            "archived_at": datetime.now(UTC).isoformat(),
        }
        await self.collection.update_one(
            {"pii_hash": pii_hash},
            {
                "$set": {
                    "fields": fields,
                    "schema_version": schema_version,
                    "updated_at": datetime.now(UTC),
                },
                "$push": {"history": history_entry},
            },
        )
