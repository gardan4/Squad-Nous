# Squad Nous — AI Chatbot for Customer Data Collection

An AI-powered chatbot that collects customer information through natural conversation.

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env with your Azure OpenAI / OpenAI credentials

# 2. Start everything
docker compose up --build

# 3. Access
# API:      http://localhost:8000
# API Docs: http://localhost:8000/docs (interactive Swagger UI)
# Frontend: http://localhost:3000
```

## Architecture

```
┌──────────────┐     ┌──────────────────────────────────────┐     ┌─────────┐
│   Frontend   │────▶│           FastAPI Backend             │────▶│ MongoDB │
│  (Next.js)   │     │                                      │     │         │
│  Port 3000   │     │  /api/session  /api/chat  /api/schema│     │Port 27017│
└──────────────┘     │                                      │     └─────────┘
                     │  ┌─────────────────────────────────┐ │
                     │  │     ConversationService          │ │
                     │  │  ┌──────────┐ ┌───────────────┐ │ │     ┌─────────┐
                     │  │  │ Schema   │ │   Duplicate   │ │ │────▶│Azure    │
                     │  │  │Extractor │ │   Detector    │ │ │     │OpenAI / │
                     │  │  └──────────┘ └───────────────┘ │ │     │OpenAI   │
                     │  │  ┌──────────────────────────────┐│ │     └─────────┘
                     │  │  │   LLM Provider Abstraction   ││ │
                     │  │  └──────────────────────────────┘│ │
                     │  └─────────────────────────────────┘ │
                     └──────────────────────────────────────┘
```

### Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Language | Python 3.13 | Latest stable, async-native, full ecosystem support |
| Web Framework | FastAPI | Async-native, auto OpenAPI docs, Pydantic validation |
| Database | MongoDB (Motor) | Schema-flexible for dynamic prompts, async driver |
| LLM | Azure OpenAI / OpenAI | Pluggable via abstract base class, OpenAI-compliant |
| Frontend | Next.js + TypeScript | Modern React, adaptive UI driven by schema endpoint |
| Container | Docker + Compose | Single-command startup, service orchestration |

## REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/session` | Create a new chat session |
| `POST` | `/api/chat` | Send a message, receive assistant response |
| `GET` | `/api/session/{id}` | Get session status and extracted fields |
| `DELETE` | `/api/session/{id}` | Close/abandon a session |
| `GET` | `/api/schema` | Get the current field schema (drives frontend UI) |
| `GET` | `/api/health` | Health check (includes database status) |

Interactive API documentation is available at `http://localhost:8000/docs` when the server is running.

### Example Conversation Flow

```bash
# 1. Create session
curl -X POST http://localhost:8000/api/session
# → {"session_id": "abc-123", "status": "active"}

# 2. Send messages
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc-123", "message": "Hi, I need a car insurance quote"}'
# → {"response": "Hello! What type of car do you have?", "status": "active", ...}

# 3. Continue until all fields collected and confirmed
# → {"response": "Registration complete!", "status": "completed", ...}
```

## Configuration

### Environment Variables (`.env`)

Secrets and environment-specific settings:

```env
LLM_PROVIDER=azure_openai          # or "openai"
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=gpt-4o
MONGODB_URL=mongodb://mongodb:27017
```

### Prompt Configuration (`config/prompt.yaml`)

Application behavior — what the chatbot collects:

```yaml
system_prompt: |
  You are an AI Assistant at a car insurance company...

expected_fields:
  - name: car_type
    type: string
    enum: ["sedan", "coupe", "station wagon", "hatchback", "minivan"]
  - name: customer_name
    type: string
    pii: true
  ...
```

**Changing the prompt changes app behavior** — different fields, different conversation flow, different database structure. No code changes needed.

## How to Swap LLM Providers

Change one environment variable:

```env
# Switch from Azure OpenAI to standard OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=your-key
```

To add a new provider (e.g., Anthropic, Ollama):
1. Create `app/services/llm/new_provider.py`
2. Subclass `BaseLLMProvider`
3. Add to `factory.py`
4. Set `LLM_PROVIDER=new_provider`

See [`docs/llm-abstraction.md`](docs/llm-abstraction.md) for details.

## Key Design Features

### Dynamic Schema Extraction
The system prompt is parsed to determine required fields. This schema drives conversation flow, function-calling tools, database structure, and the frontend UI.

### Duplicate Detection (PII-Safe)
`SHA-256(normalized_name + birthdate)` creates a fingerprint. Only the hash is stored — no PII is exposed. Duplicate registrations prompt the user to update existing records.

### Historical Data Preservation
Each registration is tagged with a `schema_version` (hash of the prompt). When the prompt changes, old data remains intact with its original schema version.

### Adaptive Frontend
The Next.js frontend queries `GET /api/schema` at load time and dynamically renders:
- Progress checklist of fields being collected
- Enum hints for constrained fields (e.g., car types)
- Adapts automatically when the prompt/schema changes

## Development

### Prerequisites
- Python 3.13+
- Docker & Docker Compose
- Node.js 22+ (for frontend development)

### Local Development

```bash
# Install Python dependencies
pip install -e ".[dev]"

# Run linter
python -m ruff check app/ tests/

# Run all tests (25 tests, ~0.3s)
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=term-missing

# Start services via Docker
docker compose up --build
```

### Build Script

```bash
./build.sh install    # Install dependencies
./build.sh lint       # Run linter
./build.sh test       # Run all tests with coverage
./build.sh build      # Build Docker images
./build.sh run        # Start services
./build.sh all        # Install, lint, test, build
```

### Testing Strategy

| Layer | Tests | Mock Strategy |
|-------|-------|--------------|
| Unit (10) | DuplicateDetector, SchemaExtractor | Pure logic, no mocks needed |
| Integration (9) | All API endpoints | mongomock-motor, mock LLM |
| E2E (2) | Full conversation + duplicate flow | mongomock-motor, stateful mock LLM |

All 25 tests run in <1s using in-memory MongoDB (mongomock-motor) — no Docker required for testing.

## Documentation

Detailed design decision documents are in the [`docs/`](docs/) folder:

| Document | Topic |
|----------|-------|
| [Architecture Overview](docs/architecture-overview.md) | System design, component diagram, data flow |
| [LLM Abstraction](docs/llm-abstraction.md) | Provider pattern, ABC vs Protocol, retry strategy |
| [Database Design](docs/database-design.md) | MongoDB document models, indexing, schema versioning |
| [Duplicate Detection](docs/duplicate-detection.md) | PII hashing, normalization, privacy considerations |
| [Schema Extraction](docs/schema-extraction.md) | Dynamic field extraction, function calling |
| [Testing Strategy](docs/testing-strategy.md) | Three-layer approach, mock strategies |
| [Error Handling](docs/error-handling.md) | Retry logic, graceful degradation |
| [Configuration](docs/configuration.md) | .env vs YAML separation |
| [Containerization](docs/containerization.md) | Multi-stage Docker, compose orchestration |
| [Frontend Design](docs/frontend-design.md) | Adaptive UI, schema-driven components |
| [Scaling Considerations](docs/scaling-considerations.md) | Horizontal scaling, production readiness |

## Project Structure

```
squad-nous/
├── app/                          # FastAPI backend
│   ├── main.py                   # App entry point + lifespan
│   ├── config.py                 # Settings + prompt config
│   ├── api/routes/               # REST API endpoints
│   ├── services/
│   │   ├── llm/                  # Pluggable LLM providers
│   │   ├── conversation.py       # Core orchestrator
│   │   ├── schema_extractor.py   # Prompt → schema
│   │   └── duplicate_detector.py # PII hashing
│   ├── models/                   # Pydantic models
│   └── db/                       # MongoDB repositories
├── frontend/                     # Next.js adaptive UI
├── config/prompt.yaml            # Configurable chatbot prompt
├── tests/                        # Unit, integration, E2E tests
├── docs/                         # Design decision documents
├── Dockerfile                    # Multi-stage Python build
├── docker-compose.yml            # Full stack orchestration
└── build.sh                      # Build/test/deploy script
```
