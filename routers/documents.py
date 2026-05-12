import asyncio
import json
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import tool
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db
from db.models import ExtractionORM
from db.repository import ExtractionRepository, SchemaRepository
from models.schemas import ExtractionResult
from services.document_service import DocumentService, get_document_service
from services.embedding import EmbeddingService, get_embedding_service


class StatusUpdate(BaseModel):
    status: Literal["accepted", "needs_review"]


class SearchRequest(BaseModel):
    q: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    answer: str
    sources: list[ExtractionResult]
    policy_updated: bool = False


class _PolicyRule(BaseModel):
    id: str
    text: str


class _UpdatePolicyInput(BaseModel):
    rules: list[_PolicyRule]


# @tool turns a function into a LangChain tool the model can call.
# The docstring becomes the tool description; the Pydantic model defines the input schema.
@tool(args_schema=_UpdatePolicyInput)
def update_policy(rules: list[_PolicyRule]) -> str:  # noqa: ARG001
    """Update the company expense policy rules. Call this when the user asks to change, add, or remove a rule. Always include ALL existing rules plus any modifications."""
    return "Policy updated successfully."

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


@router.post("/{key}/documents/search", response_model=list[ExtractionResult])
async def search_documents(
    key: str,
    body: SearchRequest,
    db: AsyncSession = Depends(get_db),
    embedding_svc: EmbeddingService = Depends(get_embedding_service),
) -> list[ExtractionResult]:
    schema = await SchemaRepository(db).get_by_key(key)
    if schema is None:
        raise HTTPException(status_code=404, detail=f"Schema '{key}' not found")

    vectors = embedding_svc.embed_texts([body.q])
    if not vectors:
        raise HTTPException(status_code=503, detail="Embedding service unavailable")

    hits = await ExtractionRepository(db).semantic_search(vectors[0], schema.id, limit=20)

    seen: set = set()
    results: list[ExtractionResult] = []
    for hit in hits:
        if hit.extraction_id not in seen:
            seen.add(hit.extraction_id)
            results.append(_orm_to_result(hit.extraction))
    return results


@router.post("/{key}/chat", response_model=ChatResponse)
async def chat_documents(
    key: str,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    embedding_svc: EmbeddingService = Depends(get_embedding_service),
) -> ChatResponse:
    schema = await SchemaRepository(db).get_by_key(key)
    if schema is None:
        raise HTTPException(status_code=404, detail=f"Schema '{key}' not found")

    repo = ExtractionRepository(db)
    context_docs = []
    source_docs = []

    vectors = embedding_svc.embed_texts([body.message])
    if vectors:
        hits = await repo.semantic_search(vectors[0], schema.id, limit=10)
        seen: set = set()
        for hit in hits:
            if hit.extraction_id not in seen:
                seen.add(hit.extraction_id)
                context_docs.append(hit.extraction)

    if not context_docs:
        all_docs = await repo.list_by_schema(schema.id)
        context_docs = all_docs[:10]

    source_docs = context_docs[:5]

    context = json.dumps(
        [{"id": str(d.id), "file_name": d.file_name, "data": d.data, "enrichments": d.enrichments}
         for d in context_docs],
        indent=2,
        default=str,
    )

    rules = (schema.validation_rules or {}).get("rules", [])
    policy_text = (
        "\n".join(f"- {r['id']}: {r['text']}" for r in rules)
        if rules else "No policy rules defined."
    )

    system_prompt = (
        "You are an assistant that answers questions about expense receipts and company expense policy. "
        "Answer concisely and accurately based on the receipt data and policy rules provided. "
        "When you reference a specific receipt, cite it inline as a markdown link using its id field: "
        "[Merchant Name](/receipts/ID). "
        "You have access to an update_policy tool — use it when the user asks to change, add, or remove a policy rule. "
        "If the answer cannot be determined from the data, say so.\n\n"
        f"Company Expense Policy:\n{policy_text}"
    )

    # Build a LangChain message list from conversation history + current turn.
    # LangChain distinguishes SystemMessage, HumanMessage, AIMessage, and ToolMessage —
    # each maps to a specific role in the provider's API.
    lc_messages: list = [SystemMessage(content=system_prompt)]
    for m in body.history:
        if m.role == "user":
            lc_messages.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            lc_messages.append(AIMessage(content=m.content))
    lc_messages.append(HumanMessage(
        content=f"Receipts:\n{context}\n\nQuestion: {body.message}"
    ))

    # bind_tools() attaches the update_policy tool to the model.
    # The model decides on its own whether to call it.
    from agents.llm import get_chat_model
    model_with_tools = get_chat_model("enrichment").bind_tools([update_policy])

    def _first_pass() -> tuple[str | None, str | None, dict | None, str | None]:
        response = model_with_tools.invoke(lc_messages)
        if response.tool_calls:
            call = response.tool_calls[0]
            return None, call["name"], call["args"], call["id"]
        return response.content, None, None, None

    def _second_pass(tool_call_id: str, tool_result: str) -> str:
        # Append the AI tool-call turn and a ToolMessage with the result,
        # then ask the model to produce the final user-facing response.
        extended = list(lc_messages)
        extended.append(AIMessage(
            content="",
            tool_calls=[{"name": "update_policy", "args": tool_input, "id": tool_call_id, "type": "tool_call"}],
        ))
        extended.append(ToolMessage(content=tool_result, tool_call_id=tool_call_id))
        chain = model_with_tools | StrOutputParser()
        return chain.invoke(extended)

    text, tool_name, tool_input, tool_call_id = await asyncio.to_thread(_first_pass)

    policy_updated = False
    if tool_name == "update_policy" and tool_input:
        rules_data = [{"id": r["id"], "text": r["text"]} for r in tool_input["rules"]]
        await SchemaRepository(db).update_validation_rules(key, rules_data)
        policy_updated = True
        answer = await asyncio.to_thread(_second_pass, tool_call_id, "Policy updated successfully.")
    else:
        answer = text or ""

    return ChatResponse(
        answer=answer,
        sources=[_orm_to_result(d) for d in source_docs],
        policy_updated=policy_updated,
    )


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
