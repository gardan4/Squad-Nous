import logging
from typing import Any

from pydantic import BaseModel

from app.config import PromptConfig
from app.services.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class FieldDefinition(BaseModel):
    name: str
    type: str  # "string", "integer", "number", "boolean"
    description: str
    required: bool = True
    format: str | None = None
    enum: list[str] | None = None
    pii: bool = False


class ExtractedSchema(BaseModel):
    title: str
    description: str
    fields: list[FieldDefinition]
    pii_fields: list[str]


class SchemaExtractor:
    def __init__(self, llm: BaseLLMProvider):
        self.llm = llm
        self._cached_schema: ExtractedSchema | None = None

    async def extract(self, prompt_config: PromptConfig) -> ExtractedSchema:
        """Extract required fields from the system prompt using the LLM."""
        if self._cached_schema is not None:
            return self._cached_schema

        meta_prompt = [
            {
                "role": "system",
                "content": (
                    "You are a schema extraction assistant. Analyze the following customer "
                    "service prompt and extract:\n"
                    "1. A short title for the service (e.g. 'Car Insurance Quote')\n"
                    "2. A one-sentence description of what the service does\n"
                    "3. ALL fields that need to be collected from the customer. For each field:\n"
                    "   - name: snake_case identifier\n"
                    "   - type: 'string', 'integer', or 'number'\n"
                    "   - description: human-readable label\n"
                    "   - enum: if the field has specific allowed values, list them\n"
                    "   - pii: true if the field is personally identifiable (name, birth date, address, etc.)\n"
                    "4. pii_fields: list of field names that are PII (used for duplicate detection)\n\n"
                    "Be thorough — extract every piece of information the prompt asks to collect."
                ),
            },
            {
                "role": "user",
                "content": f"Extract the schema from this prompt:\n\n{prompt_config.system_prompt}",
            },
        ]

        try:
            self._cached_schema = await self.llm.parse_structured(
                messages=meta_prompt,
                response_format=ExtractedSchema,
                temperature=0.1,
            )
            logger.info(
                "LLM extracted schema: '%s' with %d fields",
                self._cached_schema.title,
                len(self._cached_schema.fields),
            )
        except Exception:
            logger.exception("LLM schema extraction failed")
            raise

        return self._cached_schema

    def invalidate_cache(self):
        self._cached_schema = None

    def build_extraction_tools(self) -> list[dict[str, Any]]:
        """Build OpenAI function-calling tool definitions from the extracted schema."""
        if not self._cached_schema:
            return []

        properties: dict[str, Any] = {}
        for f in self._cached_schema.fields:
            prop: dict[str, Any] = {"type": f.type, "description": f.description}
            if f.format:
                prop["format"] = f.format
            if f.enum:
                prop["enum"] = f.enum
            properties[f.name] = prop

        return [
            {
                "type": "function",
                "function": {
                    "name": "extract_customer_data",
                    "description": (
                        "Extract and store customer data collected during conversation. "
                        "Call this whenever the customer provides information for any field. "
                        "Only include fields that the customer has explicitly provided."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "mark_registration_complete",
                    "description": (
                        "Call this ONLY when ALL required information has been collected "
                        "AND the customer has explicitly confirmed that everything is correct. "
                        "Do NOT call this until the customer confirms."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
        ]
