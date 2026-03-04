# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Squad Nous is an AI-powered chatbot for car insurance quote registration (Rabobank coding assignment). It collects customer data through natural conversation using LLM-driven extraction. The system is **schema-driven**: changing `config/prompt.yaml` changes the conversation flow, extracted fields, database structure, and frontend UI without code changes.

## Architecture

- **Frontend**: Next.js 16 (React 19, TypeScript, Tailwind CSS 4) — port 3000
- **Backend**: FastAPI (Python 3.13, async) — port 8000
- **Database**: MongoDB 7 (Motor async driver) — port 27017
- **LLM**: Pluggable providers (Azure OpenAI / OpenAI) via factory pattern

Key backend services: `ConversationService` (orchestrator) → `SchemaExtractor` (YAML→fields), `DuplicateDetector` (PII-safe SHA-256 hashing), LLM provider, `SessionRepository`, `RegistrationRepository`.

## Commands

All via `./build.sh`:

```bash
./build.sh install       # Install Python deps (uv or pip)
./build.sh lint          # Ruff linter + formatter check
./build.sh format        # Auto-format
./build.sh test          # All tests with coverage
./build.sh test-unit     # Unit tests only
./build.sh test-e2e      # E2E tests only
./build.sh build         # Docker images
./build.sh run           # Start API + MongoDB
./build.sh run-debug     # Start with Mongo Express on :8081
./build.sh stop          # Stop services
./build.sh clean         # Stop + remove volumes
./build.sh all           # install → lint → test → build
```

Docker: `docker compose up --build` for full stack. `cp .env.example .env` first.

Run a single test: `python -m pytest tests/test_api.py::test_name -v`

## Testing

Tests use **mongomock-motor** (in-memory MongoDB) and **AsyncMock** for LLM — no Docker or API keys needed. All async via pytest-asyncio. Fixtures in `tests/conftest.py`.

- Unit tests: `tests/unit/` — duplicate detector, schema extractor
- Integration tests: `tests/integration/test_api.py` — all API endpoints
- E2E tests: `tests/e2e/` — full conversation flows with stateful mock LLM

## Code Style

- **Ruff**: line length 100, rules E/F/I/N/W/UP/B/SIM, B008 excluded (FastAPI Depends)
- **mypy**: strict mode
- Fully async codebase (Motor, httpx, FastAPI)
- Dependency injection via FastAPI `Depends()` with service locator in `app/api/deps.py`
- Repository pattern for data access (`app/db/`)

## Configuration

Two-tier: environment variables (`.env` — secrets/infrastructure) + YAML (`config/prompt.yaml` — chatbot behavior/fields). Pydantic `Settings` in `app/config.py` loads env vars; `PromptConfig` loads YAML.

`prompt.yaml` defines `system_prompt` and `expected_fields` with types, enums, PII flags, and formats. Schema version is a hash of the system prompt for data migration safety.

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/session` | Create chat session |
| POST | `/api/chat` | Send message, get response + extracted fields |
| GET | `/api/session/{id}` | Session status/fields |
| DELETE | `/api/session/{id}` | Close session |
| GET | `/api/schema` | Field schema (drives frontend) |
| GET | `/api/health` | Health check with DB status |

Swagger UI at `http://localhost:8000/docs`.
