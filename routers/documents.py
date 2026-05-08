import uuid
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db
from db.models import ExtractionORM
from db.repository import ExtractionRepository, SchemaRepository
from models.schemas import ExtractionResult
from services.document_service import DocumentService, get_document_service


class StatusUpdate(BaseModel):
    status: Literal["accepted", "needs_review"]

router = APIRouter(prefix="/schemas", tags=["documents"])

_ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/pdf",
}

_MAX_FILE_SIZE = 20 * 1024 * 1024


def _orm_to_result(e: ExtractionORM) -> ExtractionResult:
    return ExtractionResult.model_validate(
        {
            "id": e.id,
            "schema_key": e.schema.key,
            "file_name": e.file_name,
            "data": e.data,
            "enrichments": e.enrichments,
            "confidence": float(e.confidence),
            "created_at": e.created_at,
        }
    )


@router.post("/{key}/documents", status_code=201, response_model=ExtractionResult)
async def upload_document(
    key: str,
    file: UploadFile = File(...),
    svc: DocumentService = Depends(get_document_service),
) -> ExtractionResult:
    content_type = (file.content_type or "").lower().split(";")[0].strip()
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{content_type}'. Accepted: {', '.join(sorted(_ALLOWED_CONTENT_TYPES))}",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(file_bytes) > _MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File exceeds the {_MAX_FILE_SIZE // (1024*1024)} MB limit")

    try:
        result = await svc.process_and_store(
            schema_key=key,
            file_bytes=file_bytes,
            file_name=file.filename,
            file_content_type=content_type,
        )
        return ExtractionResult.model_validate(result)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {exc}")


@router.get("/{key}/documents", response_model=list[ExtractionResult])
async def list_documents(
    key: str, db: AsyncSession = Depends(get_db)
) -> list[ExtractionResult]:
    schema = await SchemaRepository(db).get_by_key(key)
    if schema is None:
        raise HTTPException(status_code=404, detail=f"Schema '{key}' not found")
    extractions = await ExtractionRepository(db).list_by_schema(schema.id)
    return [_orm_to_result(e) for e in extractions]


@router.delete("/{key}/documents/{doc_id}", status_code=204)
async def delete_document(
    key: str, doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> None:
    repo = ExtractionRepository(db)
    extraction = await repo.get_by_id(doc_id)
    if extraction is None or extraction.schema.key != key:
        raise HTTPException(status_code=404, detail="Document not found")
    await repo.delete_by_id(doc_id)


@router.get("/{key}/documents/{doc_id}/file")
async def get_document_file(
    key: str, doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> Response:
    extraction = await ExtractionRepository(db).get_by_id(doc_id)
    if extraction is None or extraction.schema.key != key:
        raise HTTPException(status_code=404, detail="Document not found")
    result = await ExtractionRepository(db).get_file(doc_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No file stored for this document")
    file_data, content_type = result
    return Response(content=file_data, media_type=content_type)


@router.get("/{key}/documents/{doc_id}", response_model=ExtractionResult)
async def get_document(
    key: str, doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> ExtractionResult:
    extraction = await ExtractionRepository(db).get_by_id(doc_id)
    if extraction is None or extraction.schema.key != key:
        raise HTTPException(status_code=404, detail="Document not found")
    return _orm_to_result(extraction)


@router.patch("/{key}/documents/{doc_id}/status", response_model=ExtractionResult)
async def update_document_status(
    key: str, doc_id: uuid.UUID, body: StatusUpdate, db: AsyncSession = Depends(get_db)
) -> ExtractionResult:
    repo = ExtractionRepository(db)
    extraction = await repo.get_by_id(doc_id)
    if extraction is None or extraction.schema.key != key:
        raise HTTPException(status_code=404, detail="Document not found")
    enrichments = dict(extraction.enrichments or {})
    enrichments["status"] = body.status
    enrichments["is_compliant"] = body.status == "accepted"
    if body.status == "accepted":
        enrichments.setdefault("violations", [])
    await repo.update_enrichments(doc_id, enrichments)
    updated = await repo.get_by_id(doc_id)
    return _orm_to_result(updated)
