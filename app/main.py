import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.deps import set_services
from app.api.routes import admin, chat, health, schema
from app.config import PromptConfig, get_settings
from app.db.connection import mongodb
from app.db.registration_repo import RegistrationRepository
from app.db.session_repo import SessionRepository
from app.services.conversation import ConversationService
from app.services.duplicate_detector import DuplicateDetector
from app.services.llm.factory import create_llm_provider
from app.services.schema_extractor import SchemaExtractor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    settings = get_settings()

    # 1. Connect to MongoDB
    await mongodb.connect(
        settings.mongodb_url, settings.mongodb_database, settings.session_ttl_seconds
    )
    logger.info("Connected to MongoDB at %s", settings.mongodb_url)

    # 2. Create LLM provider
    llm = create_llm_provider(settings)
    logger.info("LLM provider: %s", settings.llm_provider)

    # 3. Load prompt config
    prompt_config = PromptConfig(settings.prompt_config_path)
    logger.info("Prompt loaded, schema version: %s", prompt_config.schema_version)

    # 4. Initialize services
    session_repo = SessionRepository()
    registration_repo = RegistrationRepository()
    schema_extractor = SchemaExtractor(llm)
    duplicate_detector = DuplicateDetector(registration_repo)

    # 5. Extract schema at startup (warm cache)
    try:
        extracted_schema = await schema_extractor.extract(prompt_config)
        logger.info("Schema extracted: %d fields", len(extracted_schema.fields))
    except Exception:
        logger.exception("Schema extraction failed at startup — will retry on first request")

    # 6. Wire up services
    conversation_service = ConversationService(
        llm=llm,
        schema_extractor=schema_extractor,
        duplicate_detector=duplicate_detector,
        session_repo=session_repo,
        registration_repo=registration_repo,
        prompt_config=prompt_config,
    )
    set_services(conversation_service, schema_extractor, prompt_config)
    logger.info("All services initialized")

    yield

    # Shutdown
    await mongodb.close()
    logger.info("MongoDB connection closed")


app = FastAPI(
    title="Squad Nous Chatbot",
    description="AI chatbot for customer data collection — Rabobank Squad Nous",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."},
    )


# Register routes
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(schema.router)
app.include_router(admin.router)
