# Document Intelligence

A multi-agent platform for extracting, enriching, and validating structured data from documents. Configured for **expense management** (receipts) out of the box — designed to support any document type without code changes.

---

## Architecture

```mermaid
graph TB
    subgraph FE["Frontend — React + Vite"]
        UI[Documents / Receipt Pages]
        Chat[Chat Panel]
        Policy[Policy Editor]
    end

    subgraph BE["Backend — FastAPI"]
        Router[Routers]
        DS[Document Service]

        subgraph Pipeline["3-Stage Agent Pipeline"]
            direction TB
            A1["Agent 1 · Extraction\nclaude-sonnet-4-6\n— forced tool use —\nextracts structured fields"]
            A2["Agent 2 · Enrichment\nclaude-haiku-4-5\n— forced tool use —\nfills semantic fields"]
            A3["Agent 3 · Validation\nclaude-haiku-4-5\n— per-rule LLM calls —\nevaluates policy compliance"]
            A1 --> A2 --> A3
        end

        Embed[Embedding Service]
    end

    subgraph DB["PostgreSQL 16 + pgvector"]
        T1[(extraction_schemas)]
        T2[(extractions)]
        T3[(extraction_embeddings)]
    end

    subgraph APIs["External APIs"]
        Anthropic[Anthropic]
        OpenAI[OpenAI]
        Gemini[Google Gemini]
    end

    FE -->|"REST / multipart"| Router
    Router --> DS
    DS --> Pipeline
    A3 --> Embed
    Embed --> T3
    DS --> T2
    Router -.-> T1

    A1 & A2 & A3 -.->|tool use| Anthropic
    Embed -.->|embeddings| OpenAI
    Embed -.->|embeddings| Gemini
```

---

## How it works

Each uploaded document flows through a three-stage pipeline:

```
Upload (image or PDF)
  │
  ▼
Agent 1 — Extraction  (claude-sonnet-4-6)
  │  Reads the document and extracts structured fields defined by the
  │  schema's tool_schema (a JSON Schema stored in the database).
  │
  ▼
Agent 2 — Enrichment  (claude-haiku-4-5)
  │  Classifies semantic fields that require understanding, not just
  │  reading (e.g. expense category: meals / transport / …).
  │  Only runs for fields listed in enrichment_fields.
  │
  ▼
Agent 3 — Validation  (claude-haiku-4-5)
  │  Evaluates each policy rule in isolation via a dedicated LLM call.
  │  Numeric rules (TYPE A) use Python comparison after LLM parsing.
  │  Non-numeric rules (TYPE B) are fully LLM-evaluated.
  │  Rules are stored in the database and editable at runtime — no redeploy needed.
  │  Produces: is_compliant, violations[], status.
  │
  ▼
Embedding + Storage
     Embeds selected fields for semantic search (pgvector).
     All results stored in PostgreSQL with the original file.
```

---

## Data model

Three tables:

```
extraction_schemas
├── key                 TEXT UNIQUE        — slug used in every API path (e.g. "receipt")
├── name / description  TEXT
├── tool_schema         JSONB              — JSON Schema for Agent 1 extraction
├── enrichments_schema  JSONB              — JSON Schema for Agent 2 + validation output
├── system_prompt       TEXT               — overrides the default Agent 1 prompt
├── embed_fields        TEXT[]             — data fields to embed for vector search
├── enrichment_fields   TEXT[]             — enrichment fields the LLM fills (Agent 2)
└── validation_rules    JSONB              — policy rules (editable at runtime)

extractions
├── schema_id   UUID FK → extraction_schemas
├── file_name   TEXT
├── file_hash   TEXT                       — SHA-256, used to detect duplicates
├── file_data   BYTEA                      — original PDF / image stored verbatim
├── data        JSONB                      — Agent 1 output
├── enrichments JSONB                      — Agent 2 + validation output
└── confidence  NUMERIC(4,3)

extraction_embeddings
├── extraction_id  UUID FK → extractions
├── field_path     TEXT                    — dot-path of embedded field
├── field_value    TEXT
└── embedding      vector(1536)            — pgvector cosine similarity search
```

### Separation of concerns

| Column | Written by | When |
|--------|-----------|------|
| `data` | Agent 1 (LLM) | Upload |
| `enrichments.category` / `summary` / `embed_text` | Agent 2 (LLM) | Upload |
| `enrichments.is_compliant` / `violations` / `status` | Agent 3 (LLM, per-rule) | Upload or re-validation |

### Receipt example

`data`:
```json
{
  "merchant_name": "Pho Saigon",
  "date": "2026-05-07",
  "total_amount": 43.50,
  "currency": "USD",
  "payment_method": "credit_card",
  "line_items": [
    { "description": "Pho Tai", "quantity": 2, "unit_price": 16.50, "total": 33.00 },
    { "description": "Spring Rolls", "quantity": 1, "unit_price": 10.50, "total": 10.50 }
  ]
}
```

`enrichments`:
```json
{
  "category": "meals",
  "summary": "Lunch for 2 at Pho Saigon — noodle soup and spring rolls",
  "is_compliant": true,
  "violations": [],
  "status": "accepted"
}
```

---

## Embeddings

Semantic search is powered by pgvector. Rather than embedding raw extracted fields directly, Agent 2 writes a dedicated `embed_text` enrichment field — a 2–3 sentence plain-English description tuned for search relevance (merchant, location, items, amount). That single field is what gets vectorized.

### How it's configured

Two places control embedding behavior:

**`config/llm_config.py`** — provider, model, and vector dimensions:

```python
embeddings=EmbeddingConfig(
    provider="openai",          # "openai" | "google" | "none"
    model="text-embedding-3-small",
    dimensions=1536,
)
```

**`config/schemas/{key}.py`** — which fields to embed:

```python
enrichment_fields=["category", "summary", "embed_text"],  # Agent 2 fills these
embed_fields=["embed_text"],                              # only this one gets vectorized
```

`embed_fields` can reference any field in `data` or `enrichments`. For nested structures (arrays of strings or objects), each leaf value is stored as a separate row in `extraction_embeddings` with a dot-notation path (e.g. `line_items.0.description`).

### Supported providers

| Provider | Models | Key env var |
|----------|--------|-------------|
| `openai` | `text-embedding-3-small` (1536-dim), `text-embedding-3-large` (3072-dim) | `OPENAI_API_KEY` |
| `google` | `text-embedding-004` (768-dim) | `GEMINI_API_KEY` |
| `none` | — | — |

Set `provider="none"` to disable embeddings entirely — the rest of the pipeline (extraction, enrichment, validation) still works. The semantic search endpoint will return no results.

### Semantic search

```bash
POST /schemas/{key}/documents/search
Content-Type: application/json

{ "query": "restaurant lunch downtown", "limit": 5 }
```

The query is embedded with the same model, then ranked by cosine similarity against all stored vectors for that schema. Results include the matched field path and similarity score alongside the full extraction.

---

## Setup

**Prerequisites:** Docker, Python 3.11+, Node.js 18+

```bash
cp .env.example .env      # fill in ANTHROPIC_API_KEY (minimum)
make setup                # install → start Postgres → migrate → seed schemas
make dev                  # API at http://localhost:8000
```

> **macOS with Homebrew:** `make` may be installed as `gmake`.

### Step by step

```bash
make install   # pip install -r requirements.txt
make db        # docker compose up -d  (Postgres 16 + pgvector)
make migrate   # alembic upgrade head
make seed      # push config/schemas/*.py to the database
make dev       # uvicorn with --reload
```

Frontend:
```bash
cd frontend && npm install && npm run dev   # http://localhost:5173
```

---

## Configuration

### LLM config — `config/llm_config.py`

Provider and model per agent; exposed read-only at `GET /config/llm`:

```python
CONFIG = LLMConfig(
    agents={
        "extraction": AgentConfig(provider="anthropic", model="claude-sonnet-4-6"),
        "enrichment": AgentConfig(provider="anthropic", model="claude-haiku-4-5-20251001"),
    },
    embeddings=EmbeddingConfig(provider="none", model="", dimensions=1536),
)
```

### Schema config — `config/schemas/receipt.py`

Each document type is a typed `SchemaConfig`:

```python
SCHEMA = SchemaConfig(
    key="receipt",
    enrichment_fields=["category", "summary", "embed_text"],
    embed_fields=["embed_text"],
    tool_schema={ ... },           # JSON Schema → Agent 1
    enrichments_schema={ ... },    # JSON Schema → Agent 2 + 3
    validation_rules=[ ... ],      # policy rules
)
```

Run `make seed` (or `make seed --force` to overwrite) to sync to the database.

### Validation rules

Rules are stored in the database and can be updated at runtime:

```bash
curl -X PUT http://localhost:8000/schemas/receipt/validation \
  -H "Content-Type: application/json" \
  -d '{
    "rules": [{
      "id": "max_meal_amount",
      "description": "Meal expenses must not exceed $50 per person"
    }]
  }'
```

After updating rules, re-run validation on existing documents without re-extracting:

```bash
curl -X POST http://localhost:8000/schemas/receipt/documents/{id}/validate
```

### Environment — `.env`

```
ANTHROPIC_API_KEY=sk-ant-...     # required
OPENAI_API_KEY=sk-...            # optional (OpenAI embeddings)
GEMINI_API_KEY=AIza...           # optional (Google embeddings)

POSTGRES_DB=automation
POSTGRES_USER=automation
POSTGRES_PASSWORD=automation
POSTGRES_PORT=5433
DATABASE_URL=postgresql+asyncpg://automation:automation@localhost:5433/automation
```

---

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/schemas` | Register an extraction schema |
| `GET` | `/schemas` | List all schemas |
| `GET` | `/schemas/{key}` | Get schema by key |
| `POST` | `/schemas/{key}/documents` | Upload a document (image or PDF) |
| `GET` | `/schemas/{key}/documents` | List all extractions |
| `GET` | `/schemas/{key}/documents/{id}` | Get a single extraction |
| `DELETE` | `/schemas/{key}/documents/{id}` | Delete an extraction |
| `GET` | `/schemas/{key}/validation` | Get current validation rules |
| `PUT` | `/schemas/{key}/validation` | Replace validation rules |
| `POST` | `/schemas/{key}/documents/{id}/validate` | Re-run validation |
| `POST` | `/schemas/{key}/documents/search` | Semantic search |
| `GET` | `/config/llm` | Get LLM configuration |
| `GET` | `/health` | Health check |

Full OpenAPI spec under `api/`, served live at `http://localhost:8000/openapi.json`.

### Upload a receipt

```bash
curl -X POST http://localhost:8000/schemas/receipt/documents \
  -F "file=@receipt.pdf"
```

---

## Adding a new document type

1. Create `config/schemas/{key}.py` with a `SCHEMA: SchemaConfig` instance.
2. Run `make seed` — the script auto-discovers all `config/schemas/*.py` files.
3. No code changes needed — the pipeline is fully schema-driven.

---

## Tests

```bash
make test          # all unit tests
pytest tests/ -v   # verbose
```

Tests are unit-only — no database, no LLM calls, no network. All providers are mocked.

---

## Project structure

```
api/                          — OpenAPI spec (YAML, split by domain)
agents/
  extraction_agent.py         — Agent 1: document → structured data
  enrichment_agent.py         — Agent 2: data → semantic fields
  providers/
    base.py                   — LLMProvider protocol
    anthropic_provider.py
    gemini_provider.py
    openai_provider.py
config/
  llm_config.py               — typed provider / model config
  settings.py                 — .env loader
  schemas/
    receipt.py                — receipt SchemaConfig
  seed_schemas.py             — auto-discovers and seeds config/schemas/*.py
db/
  models.py                   — SQLAlchemy ORM
  repository.py               — SchemaRepository, ExtractionRepository
  connection.py               — async engine + session factory
  migrations/
frontend/
  src/
    components/
      DocumentsPage.tsx       — list all documents
      ReceiptPage.tsx         — single extraction view
      PolicyPage.tsx          — edit validation rules
      PipelinePage.tsx        — view extraction schema + config
      ChatPanel.tsx           — chat with documents
models/
  schemas.py                  — Pydantic models (generated from OpenAPI spec)
routers/
  schemas.py                  — /schemas
  documents.py                — /schemas/{key}/documents
  validation.py               — /schemas/{key}/validation
  config.py                   — /config/llm
services/
  document_service.py         — orchestrates Agent 1 → 2 → 3 → storage
  ai_validator.py             — per-rule LLM validation
  embedding.py                — field extraction + vector embedding
tests/
  unit/
```
