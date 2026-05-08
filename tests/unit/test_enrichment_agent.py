"""Unit tests for the enrichment agent — provider calls are mocked."""
import pytest
from unittest.mock import MagicMock, patch

from agents.enrichment_agent import categorize_document


def _make_schema(enrichment_fields=None, enrichments_schema=None):
    schema = MagicMock()
    schema.key = "receipt"
    schema.name = "Receipt"
    schema.enrichment_fields = enrichment_fields
    schema.enrichments_schema = enrichments_schema
    return schema


class TestCategorizeDocument:
    def test_returns_empty_when_no_enrichment_fields(self):
        schema = _make_schema(enrichment_fields=None)
        result = categorize_document(extracted_data={"total_amount": 50}, schema=schema)
        assert result == {}

    def test_returns_empty_when_no_enrichments_schema(self):
        schema = _make_schema(enrichment_fields=["category"], enrichments_schema=None)
        result = categorize_document(extracted_data={"total_amount": 50}, schema=schema)
        assert result == {}

    def test_returns_empty_when_field_not_in_enrichments_schema(self):
        schema = _make_schema(
            enrichment_fields=["category"],
            enrichments_schema={"type": "object", "properties": {"status": {"type": "string"}}},
        )
        result = categorize_document(extracted_data={"total_amount": 50}, schema=schema)
        assert result == {}

    def test_calls_provider_with_correct_tool_params(self):
        enrichments_schema = {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["meals", "transport"],
                    "description": "Expense category",
                },
                "policy_compliant": {"type": "boolean"},
            },
        }
        schema = _make_schema(
            enrichment_fields=["category"],
            enrichments_schema=enrichments_schema,
        )

        mock_provider = MagicMock()
        mock_provider.call_with_tool.return_value = {"category": "meals"}

        with patch("agents.enrichment_agent.get_provider", return_value=mock_provider):
            result = categorize_document(extracted_data={"total_amount": 35}, schema=schema)

        assert result == {"category": "meals"}

        call_kwargs = mock_provider.call_with_tool.call_args.kwargs
        # Only "category" should be in tool params, not "policy_compliant"
        assert "category" in call_kwargs["tool_parameters"]["properties"]
        assert "policy_compliant" not in call_kwargs["tool_parameters"]["properties"]
        # No file bytes — this is a text-only call
        assert call_kwargs.get("file_bytes") is None

    def test_tool_name_includes_schema_key(self):
        enrichments_schema = {
            "type": "object",
            "properties": {"category": {"type": "string", "enum": ["meals"]}},
        }
        schema = _make_schema(enrichment_fields=["category"], enrichments_schema=enrichments_schema)

        mock_provider = MagicMock()
        mock_provider.call_with_tool.return_value = {"category": "meals"}

        with patch("agents.enrichment_agent.get_provider", return_value=mock_provider):
            categorize_document(extracted_data={}, schema=schema)

        call_kwargs = mock_provider.call_with_tool.call_args.kwargs
        assert call_kwargs["tool_name"] == "categorize_receipt"
