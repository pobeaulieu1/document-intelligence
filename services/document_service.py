import asyncio
import hashlib
import logging

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agents.enrichment_agent import categorize_document
from agents.extraction_agent import extract_document
from db.connection import get_db
from db.repository import ExtractionRepository, SchemaRepository
from services.ai_validator import validate_with_ai
from services.embedding import EmbeddingService, extract_embed_pairs, get_embedding_service

logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(
        self,
        schema_repo: SchemaRepository,
        extraction_repo: ExtractionRepository,
        embedding_svc: EmbeddingService,
    ) -> None:
        self._schema_repo = schema_repo
        self._extraction_repo = extraction_repo
        self._embedding_svc = embedding_svc

    async def process_and_store(
        self,
        schema_key: str,
        file_bytes: bytes,
        file_name: str | None = None,
        file_content_type: str | None = None,
    ) -> dict:
        schema = await self._schema_repo.get_by_key(schema_key)
        if schema is None:
            raise KeyError(f"Schema '{schema_key}' not found")

        # Agent 1 — extract structured data from the document
        data = await asyncio.to_thread(extract_document, file_bytes, schema)
        logger.info("Agent 1 extracted %d fields for schema '%s'", len(data), schema_key)

        # Agent 2 — LLM categorization (only fields listed in enrichment_fields)
        categorization: dict = {}
        if schema.enrichment_fields:
            try:
                categorization = await asyncio.to_thread(
                    categorize_document, data, schema, file_bytes, file_content_type
                )
                logger.info("Agent 2 categorized: %s", categorization)
            except Exception as exc:
                logger.warning("Agent 2 categorization failed, skipping: %s", exc)

        # Agent 3 — AI policy validation against plain-English rules
        rules = (schema.validation_rules or {}).get("rules", [])
        validation_result: dict = {}
        if rules:
            try:
                validation_result = await asyncio.to_thread(
                    validate_with_ai, rules, data, categorization
                )
                logger.info("Agent 3 validated: %s", validation_result.get("status"))
            except Exception as exc:
                logger.warning("Agent 3 validation failed, marking needs_review: %s", exc)
                validation_result = {
                    "is_compliant": False,
                    "violations": ["Validation unavailable — manual review required"],
                    "status": "needs_review",
                }

        enrichments = {**categorization, **validation_result}

        # Embed the fields defined on the schema
        embed_pairs = extract_embed_pairs(data, schema.embed_fields or [])
        embeddings = None
        if embed_pairs:
            vectors = self._embedding_svc.embed_texts([v for _, v in embed_pairs])
            if vectors:
                embeddings = [
                    (path, text, vec)
                    for (path, text), vec in zip(embed_pairs, vectors)
                ]

        extraction = await self._extraction_repo.save(
            schema_id=schema.id,
            data=data,
            enrichments=enrichments,
            file_hash=hashlib.sha256(file_bytes).hexdigest(),
            file_name=file_name,
            file_data=file_bytes,
            file_content_type=file_content_type,
            embeddings=embeddings,
        )

        return {
            "id": extraction.id,
            "schema_key": schema_key,
            "file_name": file_name,
            "data": data,
            "enrichments": enrichments,
            "confidence": 0.95,
            "created_at": extraction.created_at,
        }


def get_document_service(
    db: AsyncSession = Depends(get_db),
    embedding_svc: EmbeddingService = Depends(get_embedding_service),
) -> DocumentService:
    return DocumentService(
        schema_repo=SchemaRepository(db),
        extraction_repo=ExtractionRepository(db),
        embedding_svc=embedding_svc,
    )
