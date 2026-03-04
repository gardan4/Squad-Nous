from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.api.deps import set_services
from app.config import PromptConfig
from app.db.connection import mongodb
from app.db.registration_repo import RegistrationRepository
from app.db.session_repo import SessionRepository
from app.main import app
from app.services.conversation import ConversationService
from app.services.duplicate_detector import DuplicateDetector
from app.services.llm.base import BaseLLMProvider, LLMResponse
from app.services.schema_extractor import ExtractedSchema, FieldDefinition, SchemaExtractor


@pytest.fixture
def mock_llm():
    """Create a mock LLM provider."""
    provider = AsyncMock(spec=BaseLLMProvider)
    provider.chat_completion.return_value = LLMResponse(
        content=(
            "Hello! I'd be happy to help you with a car insurance quote. "
            "What type of car do you have?"
        ),
        tool_calls=[],
        finish_reason="stop",
    )
    return provider


@pytest_asyncio.fixture
async def mock_db():
    """Set up mongomock-motor for testing."""
    client = AsyncMongoMockClient()
    mongodb.client = client
    mongodb.db = client["test_db"]
    yield mongodb.db
    client.close()


@pytest.fixture
def prompt_config(tmp_path):
    """Create a test prompt config."""
    yaml_file = tmp_path / "prompt.yaml"
    yaml_file.write_text("""
system_prompt: |
  You are an AI Assistant for car insurance quotes.
  Collect: car_type, manufacturer, year_of_construction, license_plate,
  customer_name, birth_date.
  When done, include REGISTRATION_COMPLETE.

expected_fields:
  - name: car_type
    type: string
    description: "Type of car"
    enum: ["sedan", "coupe", "station wagon", "hatchback", "minivan"]
  - name: manufacturer
    type: string
    description: "Car manufacturer"
  - name: year_of_construction
    type: integer
    description: "Year of construction"
  - name: license_plate
    type: string
    description: "License plate number"
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


@pytest_asyncio.fixture
async def services(mock_db, mock_llm, prompt_config):
    """Set up all services with mocks."""
    session_repo = SessionRepository()
    registration_repo = RegistrationRepository()
    schema_extractor = SchemaExtractor(mock_llm)
    # Pre-cache schema to avoid LLM call during tests
    schema_extractor._cached_schema = ExtractedSchema(
        title="Car Insurance Quote",
        description="Collect car details for an insurance quote.",
        fields=[
            FieldDefinition(
                name="car_type",
                type="string",
                description="Type of car",
                enum=["sedan", "coupe", "station wagon", "hatchback", "minivan"],
            ),
            FieldDefinition(
                name="manufacturer", type="string", description="Car manufacturer"
            ),
            FieldDefinition(
                name="year_of_construction",
                type="integer",
                description="Year of construction",
            ),
            FieldDefinition(
                name="license_plate", type="string", description="License plate number"
            ),
            FieldDefinition(
                name="customer_name",
                type="string",
                description="Customer full name",
                pii=True,
            ),
            FieldDefinition(
                name="birth_date",
                type="string",
                description="Date of birth",
                format="date",
                pii=True,
            ),
        ],
        pii_fields=["customer_name", "birth_date"],
    )
    duplicate_detector = DuplicateDetector(registration_repo)
    conversation_service = ConversationService(
        llm=mock_llm,
        schema_extractor=schema_extractor,
        duplicate_detector=duplicate_detector,
        session_repo=session_repo,
        registration_repo=registration_repo,
        prompt_config=prompt_config,
    )
    set_services(conversation_service, schema_extractor, prompt_config)
    return {
        "conversation": conversation_service,
        "schema_extractor": schema_extractor,
        "duplicate_detector": duplicate_detector,
        "session_repo": session_repo,
        "registration_repo": registration_repo,
        "llm": mock_llm,
        "prompt_config": prompt_config,
    }


@pytest_asyncio.fixture
async def test_client(services):
    """Create a test FastAPI client with mocked dependencies."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
