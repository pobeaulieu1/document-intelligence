"""
Validation engine — deterministic rule evaluation.

Rules are stored in the database on extraction_schemas.validation_rules and are
editable at runtime via the API. This module is stateless: it receives the rules
dict and the document data/enrichments and returns a result.

Rule format:
[
  {
    "id":          "max_meal_amount",
    "description": "Meal receipts must not exceed $50",
    "source":      "data",          // "data" or "enrichments"
    "field":       "total_amount",
    "operator":    "lte",           // lte, gte, lt, gt, eq, neq, in, not_in
    "value":       50,
    "condition": {                  // optional: only apply when this holds
      "source": "enrichments",
      "field":  "category",
      "operator": "eq",
      "value":  "meals"
    },
    "message": "Meal expense exceeds the $50 per-person limit"
  }
]
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_OPERATORS = {
    "lte":    lambda a, b: a <= b,
    "gte":    lambda a, b: a >= b,
    "lt":     lambda a, b: a < b,
    "gt":     lambda a, b: a > b,
    "eq":     lambda a, b: a == b,
    "neq":    lambda a, b: a != b,
    "in":     lambda a, b: a in b,
    "not_in": lambda a, b: a not in b,
}


def _resolve(source: str, field: str, data: dict, enrichments: dict) -> Any:
    bag = data if source == "data" else enrichments
    return bag.get(field)


def _evaluate_rule(rule: dict, data: dict, enrichments: dict) -> str | None:
    """Return the violation message if the rule fails, else None."""
    condition = rule.get("condition")
    if condition:
        cond_val = _resolve(condition["source"], condition["field"], data, enrichments)
        op = _OPERATORS.get(condition["operator"])
        if op and not op(cond_val, condition["value"]):
            return None  # Condition not met — rule does not apply

    actual = _resolve(rule["source"], rule["field"], data, enrichments)
    if actual is None:
        return None  # Missing field — skip rather than auto-fail

    op = _OPERATORS.get(rule["operator"])
    if op is None:
        logger.warning("Unknown validation operator: %s", rule["operator"])
        return None

    if not op(actual, rule["value"]):
        return rule.get("message", f"Rule '{rule['id']}' violated")

    return None


def run_validation(rules: list[dict], data: dict, enrichments: dict) -> dict:
    """
    Evaluate a list of rules against extracted data and partial enrichments.

    Returns:
        is_compliant: bool
        violations:   list[str]  — one entry per violated rule
        status:       "accepted" | "needs_review"
    """
    violations: list[str] = []
    for rule in rules:
        message = _evaluate_rule(rule, data, enrichments)
        if message:
            violations.append(message)

    compliant = len(violations) == 0
    return {
        "is_compliant": compliant,
        "violations": violations,
        "status": "accepted" if compliant else "needs_review",
    }
