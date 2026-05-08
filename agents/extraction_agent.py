from agents.providers import get_provider
from db.models import ExtractionSchemaORM

_DEFAULT_SYSTEM_PROMPT = """You are an expert document parser. Extract structured data from documents with high accuracy.
Be precise with numerical values. Use null for fields that are not visible or unclear.
Always call the extraction tool with the extracted information."""


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
    """
    Extract structured data from a document using the tool schema defined on the DB schema.
    Fully generic — the tool definition comes from the database, not hardcoded here.
    """
    provider = get_provider("extraction")
    return provider.call_with_tool(
        system_prompt=schema.system_prompt or _DEFAULT_SYSTEM_PROMPT,
        user_message=f"Extract all {schema.name} data from this document.",
        tool_name=f"extract_{schema.key}",
        tool_description=schema.description or f"Extract structured {schema.name} data from a document.",
        tool_parameters=schema.tool_schema,
        file_bytes=file_bytes,
        media_type=_detect_media_type(file_bytes),
    )
