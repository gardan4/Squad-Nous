import hashlib
import unicodedata

from app.db.registration_repo import RegistrationRepository


class DuplicateDetector:
    def __init__(self, registration_repo: RegistrationRepository):
        self.repo = registration_repo

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize name for consistent hashing.

        Lowercase, strip whitespace, remove accents/diacritics, collapse spaces.
        """
        name = name.strip().lower()
        name = unicodedata.normalize("NFKD", name)
        name = "".join(c for c in name if not unicodedata.combining(c))
        name = " ".join(name.split())
        return name

    @staticmethod
    def compute_pii_hash(name: str, birthdate: str, schema_version: str = "") -> str:
        """Compute SHA-256 hash of normalized name + birthdate + schema_version.

        Including schema_version scopes duplicates per prompt/service,
        so the same person can register for different services.
        """
        normalized = (
            DuplicateDetector.normalize_name(name)
            + "|" + birthdate.strip()
            + "|" + schema_version
        )
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    async def check_duplicate(
        self, name: str, birthdate: str, schema_version: str = ""
    ) -> dict | None:
        """Check if a registration with matching PII already exists for this schema."""
        pii_hash = self.compute_pii_hash(name, birthdate, schema_version)
        return await self.repo.find_by_pii_hash(pii_hash)
