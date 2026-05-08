import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db
from db.repository import ExtractionRepository, SchemaRepository
from models.schemas import RevalidateResult, ValidationRules
from services.validation_engine import run_validation

router = APIRouter(prefix="/schemas", tags=["validation"])


@router.get("/{key}/validation", response_model=ValidationRules)
async def get_validation_rules(
    key: str, db: AsyncSession = Depends(get_db)
) -> ValidationRules:
    schema = await SchemaRepository(db).get_by_key(key)
    if schema is None:
        raise HTTPException(status_code=404, detail=f"Schema '{key}' not found")
    return ValidationRules.model_validate(schema.validation_rules or {"rules": []})


@router.put("/{key}/validation", response_model=ValidationRules)
async def update_validation_rules(
    key: str, body: ValidationRules, db: AsyncSession = Depends(get_db)
) -> ValidationRules:
    try:
        schema = await SchemaRepository(db).update_validation_rules(
            key, [r.model_dump(mode="json") for r in body.rules]
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return ValidationRules.model_validate(schema.validation_rules or {"rules": []})


@router.post("/{key}/documents/{doc_id}/validate", response_model=RevalidateResult)
async def revalidate_document(
    key: str, doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> RevalidateResult:
    """
    Re-run validation against existing extracted data using the current rules.
    Preserves LLM-produced fields (e.g. category); replaces only validation output.
    """
    extraction_repo = ExtractionRepository(db)
    extraction = await extraction_repo.get_by_id(doc_id)

    if extraction is None or extraction.schema.key != key:
        raise HTTPException(status_code=404, detail="Document not found")

    schema = extraction.schema
    rules = (schema.validation_rules or {}).get("rules", [])

    existing = extraction.enrichments or {}
    categorization = {
        k: v for k, v in existing.items()
        if k not in ("is_compliant", "violations", "status",
                     "policy_compliant", "policy_notes")
    }

    validation_result = run_validation(rules, extraction.data, categorization)
    new_enrichments = {**categorization, **validation_result}

    await extraction_repo.update_enrichments(doc_id, new_enrichments)

    return RevalidateResult(id=doc_id, schema_key=key, enrichments=new_enrichments)
