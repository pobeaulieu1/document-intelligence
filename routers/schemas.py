from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db
from db.models import ExtractionSchemaORM
from db.repository import SchemaRepository
from models.schemas import ExtractionSchema, SchemaConfig


class PolicyUpdate(BaseModel):
    rules: list[dict[str, Any]]

router = APIRouter(prefix="/schemas", tags=["schemas"])


def _orm_to_schema(s: ExtractionSchemaORM) -> ExtractionSchema:
    return ExtractionSchema.model_validate(
        {
            "id": s.id,
            "key": s.key,
            "name": s.name,
            "description": s.description,
            "tool_schema": s.tool_schema,
            "enrichments_schema": s.enrichments_schema,
            "system_prompt": s.system_prompt,
            "embed_fields": s.embed_fields,
            "enrichment_fields": s.enrichment_fields,
            "validation_rules": s.validation_rules,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        }
    )


@router.post("", status_code=201, response_model=ExtractionSchema)
async def create_schema(
    body: SchemaConfig, db: AsyncSession = Depends(get_db)
) -> ExtractionSchema:
    repo = SchemaRepository(db)
    try:
        schema = await repo.create(body.model_dump(mode="json"))
    except IntegrityError:
        raise HTTPException(status_code=409, detail=f"Schema key '{body.key}' already exists")
    return _orm_to_schema(schema)


@router.get("", response_model=list[ExtractionSchema])
async def list_schemas(db: AsyncSession = Depends(get_db)) -> list[ExtractionSchema]:
    schemas = await SchemaRepository(db).list_all()
    return [_orm_to_schema(s) for s in schemas]


@router.get("/{key}", response_model=ExtractionSchema)
async def get_schema(key: str, db: AsyncSession = Depends(get_db)) -> ExtractionSchema:
    schema = await SchemaRepository(db).get_by_key(key)
    if schema is None:
        raise HTTPException(status_code=404, detail=f"Schema '{key}' not found")
    return _orm_to_schema(schema)


@router.patch("/{key}", response_model=ExtractionSchema)
async def update_schema_policy(
    key: str, body: PolicyUpdate, db: AsyncSession = Depends(get_db)
) -> ExtractionSchema:
    try:
        schema = await SchemaRepository(db).update_validation_rules(key, body.rules)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _orm_to_schema(schema)
