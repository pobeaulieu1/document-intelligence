import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import yaml

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from config import settings
from db.connection import engine
from models.schemas import HealthResponse
from routers.config import router as config_router
from routers.documents import router as documents_router
from routers.schemas import router as schemas_router
from routers.validation import router as validation_router

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    logger.info("Agent provider configuration:")
    for agent, cfg in settings.get_agents().items():
        logger.info("  %-20s → %s (%s)", agent, cfg["provider"], cfg["model"])

    emb = settings.get_embedding_config()
    logger.info("Embeddings: %s / %s (%d dims)", emb["provider"], emb["model"], emb["dimensions"])

    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_spec: dict | None = None


def _resolve_refs(obj: object, base: Path, cache: dict) -> object:
    """Recursively inline all $ref pointers, resolving external YAML files."""
    if isinstance(obj, dict):
        if "$ref" in obj and len(obj) == 1 and isinstance(obj["$ref"], str):
            ref: str = obj["$ref"]
            if ref.startswith("#"):
                # Intra-file ref — resolve against current file's root
                parts = [p.replace("~1", "/").replace("~0", "~")
                         for p in ref.lstrip("#/").split("/") if p]
                node = cache[str(base)]
                for part in parts:
                    node = node[part]
                return _resolve_refs(node, base, cache)
            file_part, _, fragment = ref.partition("#")
            target = (base.parent / file_part).resolve()
            if str(target) not in cache:
                cache[str(target)] = yaml.safe_load(target.read_text())
            node = cache[str(target)]
            if fragment:
                for part in [p.replace("~1", "/").replace("~0", "~")
                              for p in fragment.lstrip("/").split("/") if p]:
                    node = node[part]
            return _resolve_refs(node, target, cache)
        return {k: _resolve_refs(v, base, cache) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_refs(item, base, cache) for item in obj]
    return obj


def _load_spec() -> dict:
    global _spec
    if _spec is None:
        spec_path = Path("api/openapi.yaml").resolve()
        raw = yaml.safe_load(spec_path.read_text())
        cache: dict = {str(spec_path): raw}
        _spec = _resolve_refs(raw, spec_path, cache)
    return _spec


app.openapi = _load_spec

app.include_router(schemas_router)
app.include_router(documents_router)
app.include_router(validation_router)
app.include_router(config_router)


@app.get("/health", tags=["system"], response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_includes=["*.py", "*.json", "*.yaml"],
    )
