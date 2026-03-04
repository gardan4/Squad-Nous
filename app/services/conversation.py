import json
import logging
import uuid

from app.config import PromptConfig
from app.db.registration_repo import RegistrationRepository
from app.db.session_repo import SessionRepository
from app.services.duplicate_detector import DuplicateDetector
from app.services.llm.base import BaseLLMProvider
from app.services.schema_extractor import SchemaExtractor

logger = logging.getLogger(__name__)


class ConversationService:
    """Core orchestrator for chat sessions.

    Coordinates between the LLM, schema extraction, duplicate detection,
    and MongoDB persistence to manage the full conversation lifecycle.
    """

    def __init__(
        self,
        llm: BaseLLMProvider,
        schema_extractor: SchemaExtractor,
        duplicate_detector: DuplicateDetector,
        session_repo: SessionRepository,
        registration_repo: RegistrationRepository,
        prompt_config: PromptConfig,
    ):
        self.llm = llm
        self.schema_extractor = schema_extractor
        self.duplicate_detector = duplicate_detector
        self.session_repo = session_repo
        self.registration_repo = registration_repo
        self.prompt_config = prompt_config

    async def create_session(self) -> dict:
        """Create a new chat session."""
        session_id = str(uuid.uuid4())
        await self.session_repo.create(
            session_id=session_id,
            schema_version=self.prompt_config.schema_version,
        )
        logger.info(f"Session created: {session_id}")
        return {"session_id": session_id, "status": "active"}

    async def process_message(self, session_id: str, user_message: str) -> dict:
        """Process a user message and return the assistant's response."""
        # 1. Retrieve session
        session = await self.session_repo.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        if session["status"] == "completed":
            return {
                "session_id": session_id,
                "response": "This session has already been completed.",
                "status": "completed",
                "extracted_fields": session.get("extracted_fields", {}),
            }

        # 2. Store user message
        await self.session_repo.append_message(session_id, "user", user_message)

        # 3. Build messages for LLM
        schema = await self.schema_extractor.extract(self.prompt_config)
        tools = self.schema_extractor.build_extraction_tools()

        system_content = self.prompt_config.system_prompt + (
            "\n\nIMPORTANT INSTRUCTIONS:"
            "\n- ALWAYS use the extract_customer_data tool when the customer provides or corrects any information."
            "\n- When the customer corrects a previously given value, call extract_customer_data with the updated value."
            "\n- When all information is collected and the customer confirms, call mark_registration_complete."
        )
        # Inject duplicate status context if needed
        if session["status"] == "duplicate_detected":
            system_content += (
                "\n\nA duplicate registration was found for this customer. "
                "Inform the customer that you may already have a registration on file "
                "and ask if they would like to update their existing details."
            )

        messages: list[dict[str, str]] = [{"role": "system", "content": system_content}]
        for msg in session["messages"]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})

        # 4. Call LLM with extraction tools
        try:
            llm_response = await self.llm.chat_completion(
                messages=messages,
                tools=tools if tools else None,
                temperature=0.7,
            )
        except Exception:
            logger.exception(f"LLM call failed for session {session_id}")
            return {
                "session_id": session_id,
                "response": (
                    "I'm sorry, I'm experiencing a temporary issue. "
                    "Please try sending your message again."
                ),
                "status": session["status"],
                "extracted_fields": session.get("extracted_fields", {}),
            }

        # 5. Process tool calls
        is_complete = False
        if llm_response.tool_calls:
            tool_results = []
            for tool_call in llm_response.tool_calls:
                fn_name = tool_call["function"]["name"]

                if fn_name == "extract_customer_data":
                    try:
                        extracted = json.loads(tool_call["function"]["arguments"])
                        extracted = {k: v for k, v in extracted.items() if v}
                        if extracted:
                            await self.session_repo.update_fields(session_id, extracted)
                            logger.info(
                                f"Session {session_id}: extracted {list(extracted.keys())}"
                            )
                            await self._check_duplicate(session_id, extracted, schema)
                        tool_results.append({
                            "id": tool_call["id"],
                            "result": json.dumps({"status": "ok", "saved": list(extracted.keys())}),
                        })
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse tool args: {tool_call['function']['arguments']}")
                        tool_results.append({
                            "id": tool_call["id"],
                            "result": json.dumps({"status": "error"}),
                        })

                elif fn_name == "mark_registration_complete":
                    is_complete = True
                    tool_results.append({
                        "id": tool_call["id"],
                        "result": json.dumps({"status": "ok", "registration": "complete"}),
                    })

            # If LLM only returned tool calls (no text), do a follow-up to get text
            if not llm_response.content.strip() and tool_results:
                followup_messages = list(messages)
                followup_messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {"id": tc["id"], "type": "function", "function": tc["function"]}
                        for tc in llm_response.tool_calls
                    ],
                })
                for tr in tool_results:
                    followup_messages.append({
                        "role": "tool",
                        "tool_call_id": tr["id"],
                        "content": tr["result"],
                    })
                try:
                    llm_response = await self.llm.chat_completion(
                        messages=followup_messages,
                        tools=tools if tools else None,
                        temperature=0.7,
                    )
                except Exception:
                    logger.exception(f"Follow-up LLM call failed for session {session_id}")

        # 6. Store assistant response
        assistant_content = llm_response.content or ""
        if not assistant_content.strip():
            assistant_content = "Got it, thank you! Let me continue with the next question."
        await self.session_repo.append_message(session_id, "assistant", assistant_content)

        # 7. Finalize if LLM called mark_registration_complete
        if is_complete:
            await self._finalize_registration(session_id)
            return {
                "session_id": session_id,
                "response": assistant_content,
                "status": "completed",
                "extracted_fields": (await self.session_repo.get(session_id) or {}).get(
                    "extracted_fields", {}
                ),
            }

        # 8. Return response
        updated_session = await self.session_repo.get(session_id)
        return {
            "session_id": session_id,
            "response": assistant_content,
            "status": updated_session["status"] if updated_session else "active",
            "extracted_fields": (
                updated_session.get("extracted_fields", {}) if updated_session else {}
            ),
        }

    async def _check_duplicate(self, session_id: str, extracted: dict, schema) -> None:
        """Check if PII fields indicate a duplicate registration."""
        pii_fields = schema.pii_fields
        # Find the name and birthdate field names
        name_field = next((f for f in pii_fields if "name" in f.lower()), None)
        dob_field = next(
            (f for f in pii_fields if any(kw in f.lower() for kw in ("birth", "dob", "date"))),
            None,
        )

        if not name_field or not dob_field:
            return

        # Get all extracted fields so far (not just this turn's extraction)
        session = await self.session_repo.get(session_id)
        if not session:
            return
        all_fields = session.get("extracted_fields", {})

        name_val = all_fields.get(name_field) or extracted.get(name_field)
        dob_val = all_fields.get(dob_field) or extracted.get(dob_field)

        if name_val and dob_val:
            sv = self.prompt_config.schema_version
            existing = await self.duplicate_detector.check_duplicate(name_val, str(dob_val), sv)
            if existing:
                logger.info(f"Session {session_id}: duplicate registration detected")
                await self.session_repo.set_status(session_id, "duplicate_detected")

    async def _finalize_registration(self, session_id: str) -> None:
        """Save completed registration to the registrations collection."""
        session = await self.session_repo.get(session_id)
        if not session:
            return

        fields = session.get("extracted_fields", {})
        schema = await self.schema_extractor.extract(self.prompt_config)

        # Find PII fields for hash computation
        name_val = ""
        dob_val = ""
        for pii_field in schema.pii_fields:
            val = fields.get(pii_field, "")
            if "name" in pii_field.lower():
                name_val = str(val)
            elif any(kw in pii_field.lower() for kw in ("birth", "dob", "date")):
                dob_val = str(val)

        sv = self.prompt_config.schema_version
        if not name_val or not dob_val:
            logger.warning(f"Session {session_id}: missing PII fields for hash, storing anyway")
            pii_hash = self.duplicate_detector.compute_pii_hash(
                name_val or session_id, dob_val or "unknown", sv
            )
        else:
            pii_hash = self.duplicate_detector.compute_pii_hash(name_val, dob_val, sv)

        # Check for existing registration and update or create
        existing = await self.registration_repo.find_by_pii_hash(pii_hash)
        if existing:
            await self.registration_repo.update_with_history(
                pii_hash, fields, self.prompt_config.schema_version
            )
            logger.info(f"Session {session_id}: updated existing registration")
        else:
            await self.registration_repo.create(
                pii_hash, fields, self.prompt_config.schema_version
            )
            logger.info(f"Session {session_id}: created new registration")

        await self.session_repo.set_status(session_id, "completed")

    async def get_session(self, session_id: str) -> dict | None:
        return await self.session_repo.get(session_id)

    async def close_session(self, session_id: str) -> None:
        session = await self.session_repo.get(session_id)
        if session:
            await self.session_repo.set_status(session_id, "abandoned")
