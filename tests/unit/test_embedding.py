"""Unit tests for the embedding field-extraction utility."""
import pytest

from services.embedding import extract_embed_pairs


class TestExtractEmbedPairs:
    def test_simple_string_field(self):
        pairs = extract_embed_pairs({"merchant_name": "Whole Foods"}, ["merchant_name"])
        assert pairs == [("merchant_name", "Whole Foods")]

    def test_missing_field_is_skipped(self):
        pairs = extract_embed_pairs({}, ["merchant_name"])
        assert pairs == []

    def test_empty_string_is_skipped(self):
        pairs = extract_embed_pairs({"merchant_name": ""}, ["merchant_name"])
        assert pairs == []

    def test_array_of_strings(self):
        pairs = extract_embed_pairs({"tags": ["food", "groceries"]}, ["tags"])
        assert pairs == [("tags.0", "food"), ("tags.1", "groceries")]

    def test_array_of_objects(self):
        data = {
            "line_items": [
                {"description": "Coffee", "total": 4.5},
                {"description": "Sandwich", "total": 12.0},
            ]
        }
        pairs = extract_embed_pairs(data, ["line_items"])
        descriptions = [v for _, v in pairs]
        assert "Coffee" in descriptions
        assert "Sandwich" in descriptions

    def test_array_of_objects_skips_non_string_values(self):
        data = {"line_items": [{"description": "Item", "total": 10.0}]}
        pairs = extract_embed_pairs(data, ["line_items"])
        # Only string values become pairs; numeric "total" is skipped
        paths = [p for p, _ in pairs]
        assert all("total" not in p for p in paths)

    def test_multiple_fields(self):
        data = {"merchant_name": "Starbucks", "notes": "client meeting"}
        pairs = extract_embed_pairs(data, ["merchant_name", "notes"])
        assert len(pairs) == 2

    def test_non_embed_fields_not_included(self):
        data = {"merchant_name": "Amazon", "total_amount": 99.99}
        pairs = extract_embed_pairs(data, ["merchant_name"])
        assert all("total_amount" not in p for p, _ in pairs)
