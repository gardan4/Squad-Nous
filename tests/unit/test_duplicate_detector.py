
import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient

from app.db.connection import mongodb
from app.db.registration_repo import RegistrationRepository
from app.services.duplicate_detector import DuplicateDetector


class TestNormalizeName:
    def test_strips_and_lowercases(self):
        assert DuplicateDetector.normalize_name("  John DOE  ") == "john doe"

    def test_removes_accents(self):
        assert DuplicateDetector.normalize_name("José García") == "jose garcia"

    def test_collapses_whitespace(self):
        assert DuplicateDetector.normalize_name("John    Doe") == "john doe"

    def test_handles_empty_string(self):
        assert DuplicateDetector.normalize_name("") == ""

    def test_handles_unicode(self):
        assert DuplicateDetector.normalize_name("Ångström") == "angstrom"

    def test_whitespace_only_returns_empty(self):
        assert DuplicateDetector.normalize_name("   \t  ") == ""

    def test_mixed_case_with_hyphens(self):
        assert DuplicateDetector.normalize_name("Van Der Berg-SMIT") == "van der berg-smit"


class TestComputePiiHash:
    def test_same_person_same_hash(self):
        h1 = DuplicateDetector.compute_pii_hash("John Doe", "1990-01-15")
        h2 = DuplicateDetector.compute_pii_hash("  john doe  ", "1990-01-15")
        assert h1 == h2

    def test_different_person_different_hash(self):
        h1 = DuplicateDetector.compute_pii_hash("John Doe", "1990-01-15")
        h2 = DuplicateDetector.compute_pii_hash("Jane Doe", "1990-01-15")
        assert h1 != h2

    def test_different_birthdate_different_hash(self):
        h1 = DuplicateDetector.compute_pii_hash("John Doe", "1990-01-15")
        h2 = DuplicateDetector.compute_pii_hash("John Doe", "1990-01-16")
        assert h1 != h2

    def test_hash_is_hex_string(self):
        h = DuplicateDetector.compute_pii_hash("Test", "2000-01-01")
        assert all(c in "0123456789abcdef" for c in h)
        assert len(h) == 64  # SHA-256 hex digest length

    def test_accent_insensitive(self):
        h1 = DuplicateDetector.compute_pii_hash("José García", "1985-03-20")
        h2 = DuplicateDetector.compute_pii_hash("Jose Garcia", "1985-03-20")
        assert h1 == h2

    def test_schema_version_scopes_hash(self):
        """Same person with different schema versions should produce different hashes."""
        h1 = DuplicateDetector.compute_pii_hash("John Doe", "1990-01-15", "v1")
        h2 = DuplicateDetector.compute_pii_hash("John Doe", "1990-01-15", "v2")
        assert h1 != h2

    def test_birthdate_whitespace_stripped(self):
        h1 = DuplicateDetector.compute_pii_hash("John Doe", "1990-01-15")
        h2 = DuplicateDetector.compute_pii_hash("John Doe", "  1990-01-15  ")
        assert h1 == h2


class TestCheckDuplicate:
    @pytest_asyncio.fixture
    async def detector(self):
        client = AsyncMongoMockClient()
        mongodb.client = client
        mongodb.db = client["test_dup_detector"]
        repo = RegistrationRepository()
        yield DuplicateDetector(repo), repo
        client.close()

    @pytest.mark.asyncio
    async def test_returns_none_when_no_match(self, detector):
        det, _ = detector
        result = await det.check_duplicate("John Doe", "1990-01-15", "v1")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_registration_when_match_found(self, detector):
        det, repo = detector
        pii_hash = DuplicateDetector.compute_pii_hash("John Doe", "1990-01-15", "v1")
        await repo.create(pii_hash, {"car_type": "sedan"}, "v1")

        result = await det.check_duplicate("John Doe", "1990-01-15", "v1")
        assert result is not None
        assert result["fields"]["car_type"] == "sedan"

    @pytest.mark.asyncio
    async def test_no_match_with_different_schema_version(self, detector):
        det, repo = detector
        pii_hash = DuplicateDetector.compute_pii_hash("John Doe", "1990-01-15", "v1")
        await repo.create(pii_hash, {"car_type": "sedan"}, "v1")

        # Same person, different schema version → no match
        result = await det.check_duplicate("John Doe", "1990-01-15", "v2")
        assert result is None
