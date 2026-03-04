from app.config import PromptConfig
from app.services.conversation import ConversationService
from app.services.schema_extractor import SchemaExtractor

# Service instances set during app lifespan startup
_conversation_service: ConversationService | None = None
_schema_extractor: SchemaExtractor | None = None
_prompt_config: PromptConfig | None = None


def set_services(
    conversation: ConversationService,
    extractor: SchemaExtractor,
    prompt: PromptConfig,
) -> None:
    global _conversation_service, _schema_extractor, _prompt_config
    _conversation_service = conversation
    _schema_extractor = extractor
    _prompt_config = prompt


def get_conversation_service() -> ConversationService:
    assert _conversation_service is not None, "Services not initialized"
    return _conversation_service


def get_schema_extractor() -> SchemaExtractor:
    assert _schema_extractor is not None, "Services not initialized"
    return _schema_extractor


def get_prompt_config() -> PromptConfig:
    assert _prompt_config is not None, "Services not initialized"
    return _prompt_config
