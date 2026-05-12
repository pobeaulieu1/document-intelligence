import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm import get_chat_model

logger = logging.getLogger(__name__)

_model = get_chat_model("validation")

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

_RULE_TOOL = {
    "name": "rule_values",
    "description": "Extract the limit and effective per-unit value from the expense for this rule",
    "input_schema": {
        "type": "object",
        "required": ["applies"],
        "properties": {
            "applies":        {"type": "boolean"},
            "limit_value":    {"type": "number"},
            "effective_value":{"type": "number"},
            "unit_label":     {"type": "string"},
            "violated":       {"type": "boolean"},
            "message":        {"type": "string"},
        },
    },
}


def _check_one_rule(rule: dict, data: dict, enrichments: dict) -> str | None:
    context = {**data, "expense_category": enrichments.get("category")}
    rule_text = rule.get("text", rule.get("description", ""))

    chain = _model.bind_tools(
        [_RULE_TOOL],
        tool_choice={"type": "tool", "name": "rule_values"},
    )
    response = chain.invoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Expense data:\n{json.dumps(context, indent=2, default=str)}\n\n"
            f"Rule:\n{rule_text}"
        )),
    ])
    result = response.tool_calls[0]["args"]

    if not result.get("applies", True):
        return None

    limit_val = result.get("limit_value")
    effective_val = result.get("effective_value")

    if limit_val is not None and effective_val is not None:
        if effective_val > limit_val:
            unit = result.get("unit_label", "")
            unit_str = f" {unit}" if unit else ""
            return f"${effective_val:,.2f}{unit_str} exceeds the ${limit_val:,.2f}{unit_str} limit"
        return None

    if result.get("violated"):
        return result.get("message") or f"Rule '{rule.get('id', 'unknown')}' violated"
    return None


def validate_with_ai(policy_rules: list[dict], data: dict, enrichments: dict) -> dict:
    if not policy_rules:
        return {"is_compliant": True, "violations": [], "status": "accepted"}

    violations: list[str] = []
    for rule in policy_rules:
        try:
            msg = _check_one_rule(rule, data, enrichments)
            if msg:
                violations.append(msg)
        except Exception as exc:
            logger.warning("Rule '%s' check failed: %s", rule.get("id"), exc)

    is_compliant = len(violations) == 0
    return {
        "is_compliant": is_compliant,
        "violations": violations,
        "status": "accepted" if is_compliant else "needs_review",
    }
