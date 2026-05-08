"""
Agent 2 — Enrichment.

Takes the structured data produced by Agent 1 and uses the LLM to populate the
fields in enrichments_schema that require semantic understanding (e.g. expense
category). Fields that can be computed deterministically (policy compliance,
status) are handled by the PolicyEngine, not here.

Which fields the LLM fills is controlled by the `categorize_fields` list on the
ExtractionSchemaORM. Only those fields are included in the tool call.
"""

import json

from agents.providers import get_provider
from db.models import ExtractionSchemaORM

_SYSTEM_PROMPT = (
    "You are an expert expense analyst. Given structured data extracted from a document, "
    "classify each field accurately based on its content. "
    "Always call the enrichment tool with your analysis."
)


def categorize_document(extracted_data: dict, schema: ExtractionSchemaORM) -> dict:
    """
    Use the LLM to populate the categorization fields defined on the schema.

    Returns a partial enrichments dict (only the fields listed in categorize_fields).
    Returns {} if the schema has no categorize_fields or no enrichments_schema.
    """
    categorize_fields: list[str] = schema.categorize_fields or []
    if not categorize_fields or not schema.enrichments_schema:
        return {}

    all_props: dict = schema.enrichments_schema.get("properties", {})
    cat_props = {k: v for k, v in all_props.items() if k in categorize_fields}
    if not cat_props:
        return {}

    tool_params = {
        "type": "object",
        "properties": cat_props,
        "required": categorize_fields,
    }

    provider = get_provider("enrichment")
    data_text = json.dumps(extracted_data, indent=2, default=str)

    return provider.call_with_tool(
        system_prompt=_SYSTEM_PROMPT,
        user_message=f"Classify this {schema.name} expense:\n\n{data_text}",
        tool_name=f"categorize_{schema.key}",
        tool_description=(
            f"Classify the semantic fields of a {schema.name} document. "
            f"Fields to fill: {', '.join(categorize_fields)}."
        ),
        tool_parameters=tool_params,
    )
