"""
AI-based expense policy validator.

Each policy rule is evaluated in its own focused LLM call to prevent
cross-rule contamination (e.g. confusing a $300/night accommodation limit
with an unrelated $1,000 equipment limit).

The model still reasons contextually — it can divide by number_of_nights,
count main-course portions from line_items, etc.
"""

import json
import logging

from agents.providers import get_provider

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are an expense compliance analyst evaluating ONE policy rule against an expense.\n\n"
    "Rules fall into two types — determine which applies and fill the tool accordingly:\n\n"
    "TYPE A — Numeric limit (rule contains a dollar amount or numeric threshold):\n"
    "  • limit_value:    the number from the rule text (e.g. 500 for '$500 per night').\n"
    "  • effective_value: the per-unit amount from the expense:\n"
    "      - Meals: total_amount ÷ count of main-course portions in line_items\n"
    "        (ramen, burger, entree, main dish; multiply by quantity; drinks/sides excluded).\n"
    "      - Accommodation: per-night rate from dated room-charge line items.\n"
    "        If only a lump total, divide by count of night line items.\n"
    "      - Other: use total_amount.\n"
    "  • Leave violated and message empty — the comparison is done in code.\n\n"
    "TYPE B — Non-numeric rule (merchant name, category, keyword, policy restriction):\n"
    "  • Leave limit_value and effective_value empty.\n"
    "  • violated: true if the expense breaks the rule, false otherwise.\n"
    "  • message: one sentence explaining the violation (required when violated=true).\n\n"
    "applies: set false only when the rule clearly does not concern this expense category at all."
)


def _check_one_rule(rule: dict, data: dict, enrichments: dict) -> str | None:
    """
    Evaluate a single policy rule against the expense.
    Returns a violation message string if violated, None if compliant or not applicable.
    """
    provider = get_provider("enrichment")

    context: dict = {**data, "expense_category": enrichments.get("category")}

    rule_text = rule.get("text", rule.get("description", ""))

    result = provider.call_with_tool(
        system_prompt=_SYSTEM_PROMPT,
        user_message=(
            f"Expense data:\n{json.dumps(context, indent=2, default=str)}\n\n"
            f"Rule:\n{rule_text}"
        ),
        tool_name="rule_values",
        tool_description="Extract the limit and effective per-unit value from the expense for this rule",
        tool_parameters={
            "type": "object",
            "required": ["applies"],
            "properties": {
                "applies": {
                    "type": "boolean",
                    "description": "False only if this rule clearly does not concern this expense category.",
                },
                "limit_value": {
                    "type": "number",
                    "description": "TYPE A only — numeric limit from the rule text (e.g. 500).",
                },
                "effective_value": {
                    "type": "number",
                    "description": "TYPE A only — computed per-unit amount from the expense.",
                },
                "unit_label": {
                    "type": "string",
                    "description": "TYPE A only — unit for the violation message (e.g. 'per night', 'per person').",
                },
                "violated": {
                    "type": "boolean",
                    "description": "TYPE B only — true if the expense breaks the non-numeric rule.",
                },
                "message": {
                    "type": "string",
                    "description": "TYPE B only — violation explanation, required when violated=true.",
                },
            },
        },
    )

    if not result.get("applies", True):
        return None

    limit_val = result.get("limit_value")
    effective_val = result.get("effective_value")

    # Type A — numeric comparison done in Python
    if limit_val is not None and effective_val is not None:
        if effective_val > limit_val:
            unit = result.get("unit_label", "")
            unit_str = f" {unit}" if unit else ""
            return (
                f"${effective_val:,.2f}{unit_str} exceeds "
                f"the ${limit_val:,.2f}{unit_str} limit"
            )
        return None

    # Type B — non-numeric rule, trust the AI verdict
    if result.get("violated"):
        return result.get("message") or f"Rule '{rule.get('id', 'unknown')}' violated"
    return None


def validate_with_ai(
    policy_rules: list[dict],
    data: dict,
    enrichments: dict,
) -> dict:
    """
    Evaluate each policy rule independently to avoid cross-rule confusion.

    Returns:
        {is_compliant: bool, violations: list[str], status: "accepted"|"needs_review"}
    """
    if not policy_rules:
        return {"is_compliant": True, "violations": [], "status": "accepted"}

    violations: list[str] = []
    for rule in policy_rules:
        try:
            message = _check_one_rule(rule, data, enrichments)
            if message:
                violations.append(message)
        except Exception as exc:
            logger.warning("Rule '%s' check failed: %s", rule.get("id"), exc)

    is_compliant = len(violations) == 0
    return {
        "is_compliant": is_compliant,
        "violations": violations,
        "status": "accepted" if is_compliant else "needs_review",
    }
