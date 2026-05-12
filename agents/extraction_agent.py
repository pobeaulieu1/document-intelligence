import base64

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm import get_chat_model
from db.models import ExtractionSchemaORM

_model = get_chat_model("extraction")

_DEFAULT_SYSTEM_PROMPT = (
    "You are an expert document parser. Extract structured data from documents with high accuracy. "
    "Be precise with numerical values. Use null for fields that are not visible or unclear. "
    "Always call the extraction tool with the extracted information."
)


def _detect_media_type(file_bytes: bytes) -> str:
    if file_bytes[:4] == b"%PDF":
        return "application/pdf"
    if file_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if file_bytes[:2] == b"\xff\xd8":
        return "image/jpeg"
    if file_bytes[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if len(file_bytes) >= 12 and file_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def extract_document(file_bytes: bytes, schema: ExtractionSchemaORM) -> dict:
    media_type = _detect_media_type(file_bytes)
    b64 = base64.standard_b64encode(file_bytes).decode()

    content: list = []
    if media_type == "application/pdf":
        content.append({
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": b64},
        })
    else:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": b64},
        })
    content.append({"type": "text", "text": f"Extract all {schema.name} data from this document."})

    tool_name = f"extract_{schema.key}"
    chain = _model.bind_tools(
        [{"name": tool_name, "description": schema.description or f"Extract {schema.name} data.", "input_schema": schema.tool_schema}],
        tool_choice={"type": "tool", "name": tool_name},
    )
    response = chain.invoke([
        SystemMessage(content=schema.system_prompt or _DEFAULT_SYSTEM_PROMPT),
        HumanMessage(content=content),
    ])
    return response.tool_calls[0]["args"]
