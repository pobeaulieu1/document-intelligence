# Document Intelligence Platform

A generic multi-agent platform for extracting, classifying, and validating structured data from documents. Configured for **expense management** (receipts) out of the box — designed to support any document type without code changes.

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
  │  Classifies semantic fields that require understanding of the content,
  │  not just reading it (e.g. expense category: meals / transport / …).
  │  Only runs for fields listed in the schema's categorize_fields.
  │
  ▼
Validation Engine  (deterministic)
  │  Evaluates configurable rules against the extracted data and
  │  enrichments. Rules are stored in the database and editable at
  │  runtime via the API — no redeploy needed.
  │  Produces: is_compliant, violations[], status.
  │
  ▼
PostgreSQL + pgvector
     Stores data (Agent 1) and enrichments (Agent 2 + validation)
     in separate JSONB columns. Embeds selected fields for semantic search.
```

---

## Data model

Three tables, one schema:

```
extraction_schemas
├── id            UUID PK
├── key           TEXT UNIQUE        — slug used in every API path (e.g. "receipt")
├── name          TEXT               — human-readable label
├── description   TEXT
├── tool_schema   JSONB              — JSON Schema for Agent 1 extraction
├── enrichments_schema JSONB         — JSON Schema describing Agent 2 + validation output
├── system_prompt TEXT               — overrides the default Agent 1 prompt
├── embed_fields  TEXT[]             — data fields to embed for vector search
├── categorize_fields TEXT[]         — enrichment fields the LLM fills (Agent 2)
├── validation_rules JSONB           — rules evaluated by the validation engine
├── created_at    TIMESTAMPTZ
└── updated_at    TIMESTAMPTZ

extractions
├── id            UUID PK
├── schema_id     UUID FK → extraction_schemas.id  (CASCADE DELETE)
├── file_name     TEXT
├── file_hash     TEXT               — SHA-256, used to detect duplicates
├── data          JSONB              — Agent 1 output; shape matches tool_schema
├── enrichments   JSONB              — Agent 2 + validation output; includes
│                                      category, is_compliant, violations, status
├── confidence    NUMERIC(4,3)
└── created_at    TIMESTAMPTZ

extraction_embeddings
├── id            UUID PK
├── extraction_id UUID FK → extractions.id  (CASCADE DELETE)
├── field_path    TEXT               — dot-path of the embedded field (e.g. "merchant_name")
├── field_value   TEXT               — text that was embedded
└── embedding     vector(768)        — pgvector column for similarity search
```

### Separation of concerns

| Column | Who writes it | When |
|--------|--------------|------|
| `data` | Agent 1 (LLM) | At upload time |
| `enrichments.category` | Agent 2 (LLM) | At upload time |
| `enrichments.is_compliant` / `violations` / `status` | Validation engine (deterministic) | At upload time, or re-triggered via `POST …/validate` |

The `validation_rules` on a schema can be updated at any time via `PUT /schemas/{key}/validation`. Re-running `POST /schemas/{key}/documents/{id}/validate` applies the new rules to an existing extraction without touching Agent 1/2 output.

### Receipt schema (example)

The `data` column for a receipt looks like:

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

The `enrichments` column:

```json
{
  "category": "meals",
  "is_compliant": true,
  "violations": [],
  "status": "accepted"
}
```

---

## Setup

**Prerequisites:** Docker, Python 3.11+

```bash
cp .env.example .env      # fill in ANTHROPIC_API_KEY (minimum)
make setup                # install → start Postgres → migrate → seed schemas
make dev                  # start the API at http://localhost:8000
```

> **macOS with Homebrew:** `make` may be installed as `gmake`. Use `gmake` for all commands.

### Step by step

```bash
make install   # pip install -r requirements.txt
make db        # docker compose up -d  (Postgres 16 + pgvector)
make migrate   # alembic upgrade head
make seed      # insert the receipt schema into the database
make dev       # uvicorn with --reload
```

---

## Configuration

### LLM config — `config/llm_config.py`

Provider and model per agent, written as typed Python (type-checked at import time):

```python
from models.schemas import AgentConfig, EmbeddingConfig, LLMConfig

CONFIG = LLMConfig(
    agents={
        "extraction": AgentConfig(provider="anthropic", model="claude-sonnet-4-6"),
        "enrichment": AgentConfig(provider="anthropic", model="claude-haiku-4-5-20251001"),
    },
    embeddings=EmbeddingConfig(provider="none", model="", dimensions=768),
)
```

Exposed read-only at `GET /config/llm`.

### Schema config — `config/schemas/receipt.py`

Each document type is a `SchemaConfig` instance — also typed Python, not YAML or JSON:

```python
SCHEMA = SchemaConfig(
    key="receipt",
    categorize_fields=["category"],
    embed_fields=["merchant_name", "line_items"],
    tool_schema={ ... },           # JSON Schema for Agent 1
    enrichments_schema={ ... },    # JSON Schema for Agent 2 + validation output
    validation_rules=ValidationRules(rules=[
        ValidationRule(
            id="max_meal_amount",
            source=Source.data, field="total_amount",
            operator=Operator.lte, value=50,
            condition=ValidationRuleCondition(
                source=Source.enrichments, field="category",
                operator=Operator.eq, value="meals",
            ),
            message="Meal expense exceeds the $50 per-person limit",
        ),
        ...
    ]),
)
```

Run `make seed` (or `make seed --force` to overwrite) to push configs to the database.

### Validation rules

Rules can also be updated at runtime — no redeploy:

```bash
curl -X PUT http://localhost:8000/schemas/receipt/validation \
  -H "Content-Type: application/json" \
  -d '{
    "rules": [{
      "id": "max_meal_amount",
      "source": "data", "field": "total_amount",
      "operator": "lte", "value": 75,
      "condition": { "source": "enrichments", "field": "category", "operator": "eq", "value": "meals" },
      "message": "Meal expense exceeds the $75 per-person limit"
    }]
  }'
```

Supported operators: `lte`, `gte`, `lt`, `gt`, `eq`, `neq`, `in`, `not_in`.

### Environment — `.env`

```
ANTHROPIC_API_KEY=sk-ant-...     # required
GEMINI_API_KEY=AIza...           # optional (only for Google embeddings)

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
| `GET` | `/schemas/{key}/documents` | List all extractions for a schema |
| `GET` | `/schemas/{key}/documents/{id}` | Get a single extraction |
| `GET` | `/schemas/{key}/validation` | Get current validation rules |
| `PUT` | `/schemas/{key}/validation` | Replace validation rules |
| `POST` | `/schemas/{key}/documents/{id}/validate` | Re-run validation on an existing extraction |
| `GET` | `/config/llm` | Get LLM provider configuration |
| `GET` | `/health` | Health check |

The full OpenAPI spec is split by domain under `api/` and served live at `http://localhost:8000/openapi.json`.

### Upload a receipt

```bash
curl -X POST http://localhost:8000/schemas/receipt/documents \
  -F "file=@receipt.pdf"
```

### Example response

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "schema_key": "receipt",
  "file_name": "lunch.pdf",
  "created_at": "2026-05-08T15:30:00Z",
  "confidence": 0.95,
  "data": {
    "merchant_name": "Pho Saigon",
    "date": "2026-05-07",
    "total_amount": 87.50,
    "currency": "USD",
    "payment_method": "credit_card",
    "line_items": [
      { "description": "Pho Tai", "quantity": 2, "unit_price": 16.50, "total": 33.00 }
    ]
  },
  "enrichments": {
    "category": "meals",
    "is_compliant": false,
    "violations": ["Meal expense exceeds the $50 per-person limit"],
    "status": "needs_review"
  }
}
```

---

## Adding a new document type

1. Create `config/schemas/{key}.py` with a `SCHEMA: SchemaConfig` instance.
2. Run `make seed` — the script auto-discovers all `config/schemas/*.py` files.
3. No code changes needed — the pipeline is fully schema-driven.

---

## Tests

```bash
make test                   # run all unit tests
pytest tests/ -v            # verbose
```

Tests are unit-only — no database, no LLM calls, no network. All providers are mocked.

---

## Project structure

```
api/
  openapi.yaml              — root spec (aggregates domain files)
  schemas.yaml              — schema management types + paths
  documents.yaml            — document upload/retrieval types + paths
  validation.yaml           — validation rule types + paths
  config.yaml               — LLM config types + path
  common.yaml               — shared: HTTPError, HealthResponse, SchemaKey param

agents/
  extraction_agent.py       — Agent 1: document → structured data (LLM)
  enrichment_agent.py       — Agent 2: data → semantic fields (LLM)
  providers/
    base.py                 — LLMProvider protocol
    anthropic_provider.py
    gemini_provider.py

config/
  llm_config.py             — typed provider/model config (LLMConfig)
  settings.py               — reads .env, exposes get_agent_config() etc.
  schemas/
    receipt.py              — receipt SchemaConfig (typed Python)
  seed_schemas.py           — seeds config/schemas/*.py into the database

db/
  models.py                 — SQLAlchemy ORM (ExtractionSchemaORM, ExtractionORM, …)
  repository.py             — SchemaRepository, ExtractionRepository
  connection.py             — async engine + session factory
  alembic.ini               — Alembic config
  migrations/
    versions/
      0001_initial.py       — single squashed migration

models/
  schemas.py                — Pydantic models (auto-generated from openapi.yaml)

routers/
  schemas.py                — POST/GET /schemas
  documents.py              — POST/GET /schemas/{key}/documents
  validation.py             — GET/PUT /schemas/{key}/validation, POST …/validate
  config.py                 — GET /config/llm

services/
  document_service.py       — orchestrates Agent 1 → Agent 2 → validation → storage
  validation_engine.py      — deterministic rule evaluator
  embedding.py              — field extraction + vector embedding

tests/
  unit/
    test_validation_engine.py
    test_embedding.py
    test_enrichment_agent.py
```
