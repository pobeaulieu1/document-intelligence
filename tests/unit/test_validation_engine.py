"""
Unit tests for the validation engine.

All tests are offline — no DB, no LLM, no network.
Rules are passed directly as dicts (same format stored in DB).
"""
import pytest

from services.validation_engine import _evaluate_rule, run_validation

_RECEIPT_RULES = [
    {
        "id": "max_meal_amount",
        "source": "data",
        "field": "total_amount",
        "operator": "lte",
        "value": 50,
        "condition": {"source": "enrichments", "field": "category", "operator": "eq", "value": "meals"},
        "message": "Meal expense exceeds the $50 per-person limit",
    },
    {
        "id": "max_transport_amount",
        "source": "data",
        "field": "total_amount",
        "operator": "lte",
        "value": 200,
        "condition": {"source": "enrichments", "field": "category", "operator": "eq", "value": "transport"},
        "message": "Transport expense exceeds the $200 per-trip limit",
    },
    {
        "id": "max_equipment_amount",
        "source": "data",
        "field": "total_amount",
        "operator": "lte",
        "value": 1000,
        "condition": {"source": "enrichments", "field": "category", "operator": "eq", "value": "equipment"},
        "message": "Equipment purchase exceeds the $1000 limit and requires pre-approval",
    },
    {
        "id": "allowed_categories",
        "source": "enrichments",
        "field": "category",
        "operator": "in",
        "value": ["meals", "transport", "accommodation", "equipment", "other"],
        "message": "Expense category is not in the approved list",
    },
]


class TestEvaluateRule:
    def _rule(self, **kwargs) -> dict:
        base = {
            "id": "test_rule",
            "source": "data",
            "field": "total_amount",
            "operator": "lte",
            "value": 100,
            "message": "Too expensive",
        }
        base.update(kwargs)
        return base

    def test_passes_when_condition_not_met(self):
        rule = self._rule(
            condition={"source": "enrichments", "field": "category", "operator": "eq", "value": "meals"}
        )
        result = _evaluate_rule(rule, data={"total_amount": 999}, enrichments={"category": "transport"})
        assert result is None

    def test_fails_when_value_exceeds_limit(self):
        result = _evaluate_rule(self._rule(), data={"total_amount": 150}, enrichments={})
        assert result == "Too expensive"

    def test_passes_when_value_within_limit(self):
        result = _evaluate_rule(self._rule(), data={"total_amount": 50}, enrichments={})
        assert result is None

    def test_skips_when_field_missing(self):
        result = _evaluate_rule(self._rule(), data={}, enrichments={})
        assert result is None

    def test_in_operator_pass(self):
        rule = self._rule(field="category", operator="in", value=["meals", "transport"], source="enrichments")
        result = _evaluate_rule(rule, data={}, enrichments={"category": "meals"})
        assert result is None

    def test_in_operator_fail(self):
        rule = self._rule(
            field="category", operator="in", value=["meals", "transport"],
            source="enrichments", message="Bad category",
        )
        result = _evaluate_rule(rule, data={}, enrichments={"category": "personal"})
        assert result == "Bad category"

    def test_unknown_operator_skips(self):
        result = _evaluate_rule(self._rule(operator="unknown_op"), data={"total_amount": 9999}, enrichments={})
        assert result is None


class TestRunValidation:
    def test_empty_rules_is_compliant(self):
        result = run_validation([], data={}, enrichments={})
        assert result["is_compliant"] is True
        assert result["status"] == "accepted"
        assert result["violations"] == []

    def test_compliant_meal_under_limit(self):
        result = run_validation(
            _RECEIPT_RULES,
            data={"total_amount": 35},
            enrichments={"category": "meals"},
        )
        assert result["is_compliant"] is True
        assert result["status"] == "accepted"
        assert result["violations"] == []

    def test_non_compliant_meal_over_limit(self):
        result = run_validation(
            _RECEIPT_RULES,
            data={"total_amount": 85},
            enrichments={"category": "meals"},
        )
        assert result["is_compliant"] is False
        assert result["status"] == "needs_review"
        assert any("$50" in v for v in result["violations"])

    def test_compliant_transport_under_limit(self):
        result = run_validation(
            _RECEIPT_RULES,
            data={"total_amount": 45},
            enrichments={"category": "transport"},
        )
        assert result["is_compliant"] is True

    def test_non_compliant_transport_over_limit(self):
        result = run_validation(
            _RECEIPT_RULES,
            data={"total_amount": 250},
            enrichments={"category": "transport"},
        )
        assert result["is_compliant"] is False
        assert result["status"] == "needs_review"

    def test_equipment_at_limit_is_compliant(self):
        result = run_validation(
            _RECEIPT_RULES,
            data={"total_amount": 1000},
            enrichments={"category": "equipment"},
        )
        assert result["is_compliant"] is True

    def test_equipment_over_limit_needs_review(self):
        result = run_validation(
            _RECEIPT_RULES,
            data={"total_amount": 1500},
            enrichments={"category": "equipment"},
        )
        assert result["is_compliant"] is False

    def test_unapproved_category_fails(self):
        result = run_validation(
            _RECEIPT_RULES,
            data={"total_amount": 9999},
            enrichments={"category": "personal"},
        )
        assert result["is_compliant"] is False
        assert len(result["violations"]) >= 1
