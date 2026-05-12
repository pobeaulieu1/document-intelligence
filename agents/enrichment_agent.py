import base64
import json

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm import get_chat_model
from db.models import ExtractionSchemaORM

_model = get_chat_model("enrichment")

_SYSTEM_PROMPT = (
    "You are an expert expense analyst. You are given structured data extracted from a receipt "
    "and, when available, the original receipt image or PDF. "
    "Use both sources — especially the original document — to classify each field accurately. "
    "For embed_text, write 2-3 sentences covering only what someone would search for: "
    "merchant name, city/location, delivery platform if any, what was purchased, and total amount. "
    "Be concise — omit tax lines, fees, and formatting details. "
    "Always call the enrichment tool with your analysis."
)


def categorize_document(
    extracted_data: dict,
    schema: ExtractionSchemaORM,
    file_bytes: bytes | None = None,
    media_type: str | None = None,
) -> dict:
    enrichment_fields: list[str] = schema.enrichment_fields or []
    if not enrichment_fields or not schema.enrichments_schema:
        return {}

    all_props: dict = schema.enrichments_schema.get("properties", {})
    cat_props = {k: v for k, v in all_props.items() if k in enrichment_fields}
    if not cat_props:
        return {}

    tool_name = f"categorize_{schema.key}"
    tool_params = {"type": "object", "properties": cat_props, "required": enrichment_fields}
    data_text = json.dumps(extracted_data, indent=2, default=str)

    content: list = []
    if file_bytes is not None:
        b64 = base64.standard_b64encode(file_bytes).decode()
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
    content.append({"type": "text", "text": (
        f"Classify this {schema.name} expense.\n\n"
        f"Structured data:\n{data_text}\n\n"
        f"{'The original receipt is attached — use it to fill embed_text with everything visible.' if file_bytes else ''}"
    )})

    chain = _model.bind_tools(
        [{"name": tool_name, "description": f"Classify fields: {', '.join(enrichment_fields)}.", "input_schema": tool_params}],
        tool_choice={"type": "tool", "name": tool_name},
    )
    response = chain.invoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=content),
    ])
    return response.tool_calls[0]["args"]
