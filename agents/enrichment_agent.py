"""
Agent 2 — Enrichment.

Takes the structured data produced by Agent 1 and uses the LLM to populate the
fields in enrichments_schema that require semantic understanding (e.g. expense
category). Fields that can be computed deterministically (policy compliance,
status) are handled by the PolicyEngine, not here.

Which fields the LLM fills is controlled by the `enrichment_fields` list on the
ExtractionSchemaORM. Only those fields are included in the tool call.
"""

import json

from agents.providers import get_provider
from db.models import ExtractionSchemaORM

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
    """
    Use the LLM to populate the categorization fields defined on the schema.

    Returns a partial enrichments dict (only the fields listed in enrichment_fields).
    Returns {} if the schema has no enrichment_fields or no enrichments_schema.
    """
    enrichment_fields: list[str] = schema.enrichment_fields or []
    if not enrichment_fields or not schema.enrichments_schema:
        return {}

    all_props: dict = schema.enrichments_schema.get("properties", {})
    cat_props = {k: v for k, v in all_props.items() if k in enrichment_fields}
    if not cat_props:
        return {}

    tool_params = {
        "type": "object",
        "properties": cat_props,
        "required": enrichment_fields,
    }

    provider = get_provider("enrichment")
    data_text = json.dumps(extracted_data, indent=2, default=str)

    return provider.call_with_tool(
        system_prompt=_SYSTEM_PROMPT,
        user_message=(
            f"Classify this {schema.name} expense.\n\n"
            f"Structured data:\n{data_text}\n\n"
            f"{'The original receipt is attached — use it to fill embed_text with everything visible.' if file_bytes else ''}"
        ),
        tool_name=f"categorize_{schema.key}",
        tool_description=(
            f"Classify the semantic fields of a {schema.name} document. "
            f"Fields to fill: {', '.join(enrichment_fields)}."
        ),
        tool_parameters=tool_params,
        file_bytes=file_bytes,
        media_type=media_type,
    )
