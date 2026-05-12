import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import ExtractionEmbeddingORM, ExtractionORM, ExtractionSchemaORM


class SchemaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict) -> ExtractionSchemaORM:
        schema = ExtractionSchemaORM(**data)
        self._session.add(schema)
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raise
        await self._session.refresh(schema)
        return schema

    async def get_by_key(self, key: str) -> ExtractionSchemaORM | None:
        result = await self._session.execute(
            select(ExtractionSchemaORM).where(ExtractionSchemaORM.key == key)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[ExtractionSchemaORM]:
        result = await self._session.execute(select(ExtractionSchemaORM))
        return list(result.scalars().all())

    async def update_validation_rules(self, key: str, rules: list[dict]) -> ExtractionSchemaORM:
        schema = await self.get_by_key(key)
        if schema is None:
            raise KeyError(f"Schema '{key}' not found")
        schema.validation_rules = {"rules": rules}
        await self._session.commit()
        await self._session.refresh(schema)
        return schema


class ExtractionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(
        self,
        schema_id: uuid.UUID,
        data: dict,
        enrichments: dict | None = None,
        file_hash: str | None = None,
        file_name: str | None = None,
        file_data: bytes | None = None,
        file_content_type: str | None = None,
        confidence: float = 0.95,
        embeddings: list[tuple[str, str, list[float]]] | None = None,
    ) -> ExtractionORM:
        extraction = ExtractionORM(
            schema_id=schema_id,
            data=data,
            enrichments=enrichments,
            file_hash=file_hash,
            file_name=file_name,
            file_data=file_data,
            file_content_type=file_content_type,
            confidence=confidence,
        )
        if embeddings:
            for field_path, field_value, vector in embeddings:
                extraction.embeddings.append(
                    ExtractionEmbeddingORM(
                        field_path=field_path,
                        field_value=field_value,
                        embedding=vector,
                    )
                )
        self._session.add(extraction)
        await self._session.commit()
        await self._session.refresh(extraction)
        return extraction

    async def update_enrichments(self, extraction_id: uuid.UUID, enrichments: dict) -> None:
        """Overwrite the enrichments on an existing extraction (e.g. re-run Agent 2)."""
        result = await self._session.execute(
            select(ExtractionORM).where(ExtractionORM.id == extraction_id)
        )
        extraction = result.scalar_one_or_none()
        if extraction is None:
            raise KeyError(f"Extraction {extraction_id} not found")
        extraction.enrichments = enrichments
        await self._session.commit()

    async def delete_by_id(self, extraction_id: uuid.UUID) -> None:
        result = await self._session.execute(
            select(ExtractionORM).where(ExtractionORM.id == extraction_id)
        )
        row = result.scalar_one_or_none()
        if row:
            await self._session.delete(row)
            await self._session.commit()

    async def get_file(self, extraction_id: uuid.UUID) -> tuple[bytes, str] | None:
        """Return (file_data, content_type) without loading the full ORM row."""
        result = await self._session.execute(
            select(ExtractionORM.file_data, ExtractionORM.file_content_type)
            .where(ExtractionORM.id == extraction_id)
        )
        row = result.one_or_none()
        if row is None or row.file_data is None:
            return None
        return (row.file_data, row.file_content_type or "application/octet-stream")

    async def get_by_id(self, extraction_id: uuid.UUID) -> ExtractionORM | None:
        result = await self._session.execute(
            select(ExtractionORM)
            .options(selectinload(ExtractionORM.schema))
            .where(ExtractionORM.id == extraction_id)
        )
        return result.scalar_one_or_none()

    async def list_by_schema(self, schema_id: uuid.UUID) -> list[ExtractionORM]:
        result = await self._session.execute(
            select(ExtractionORM)
            .options(selectinload(ExtractionORM.schema))
            .where(ExtractionORM.schema_id == schema_id)
            .order_by(ExtractionORM.created_at.desc())
        )
        return list(result.scalars().all())

    async def semantic_search(
        self,
        query_embedding: list[float],
        schema_id: uuid.UUID | None = None,
        limit: int = 10,
        max_distance: float = 0.5,
    ) -> list[ExtractionEmbeddingORM]:
        query = (
            select(ExtractionEmbeddingORM)
            .options(
                selectinload(ExtractionEmbeddingORM.extraction)
                .selectinload(ExtractionORM.schema)
            )
            .where(ExtractionEmbeddingORM.embedding.cosine_distance(query_embedding) < max_distance)
            .order_by(ExtractionEmbeddingORM.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        if schema_id:
            query = query.join(ExtractionORM).where(ExtractionORM.schema_id == schema_id)
        result = await self._session.execute(query)
        return list(result.scalars().all())
