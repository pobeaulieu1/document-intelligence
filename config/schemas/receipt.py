from models.schemas import PolicyRule, SchemaConfig, ValidationRules

SCHEMA = SchemaConfig(
    key="receipt",
    name="Receipt",
    description="Extract structured data from retail and restaurant receipts",
    categorize_fields=["category", "summary"],
    embed_fields=["merchant_name", "line_items"],
    tool_schema={
        "type": "object",
        "required": ["merchant_name", "total_amount", "currency", "line_items"],
        "properties": {
            "merchant_name": {"type": "string", "description": "Name of the merchant or store"},
            "date": {"type": "string", "description": "Date of purchase in YYYY-MM-DD format"},
            "total_amount": {"type": "number", "description": "Total amount paid"},
            "currency": {"type": "string", "description": "ISO 4217 currency code", "default": "USD"},
            "payment_method": {
                "type": ["string", "null"],
                "enum": ["cash", "credit_card", "debit_card", "check", "other", None],
                "description": "Payment method used",
            },
            "line_items": {
                "type": "array",
                "description": "Individual items on the receipt",
                "items": {
                    "type": "object",
                    "required": ["description", "unit_price", "total"],
                    "properties": {
                        "description": {"type": "string"},
                        "quantity": {"type": "number", "default": 1.0},
                        "unit_price": {"type": "number"},
                        "total": {"type": "number"},
                    },
                },
            },
        },
    },
    enrichments_schema={
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["meals", "transport", "accommodation", "equipment", "other"],
                "description": "Expense category — classified by Agent 2",
            },
            "summary": {
                "type": "string",
                "description": "One sentence summarising the purpose of this expense (who, what, where, when).",
            },
            "is_compliant": {
                "type": "boolean",
                "description": "Whether the expense satisfies all policy rules",
            },
            "violations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of violated rules, empty when compliant",
            },
            "status": {
                "type": "string",
                "enum": ["accepted", "needs_review"],
                "description": "accepted when is_compliant is true, needs_review otherwise",
            },
        },
    },
    validation_rules=ValidationRules(
        rules=[
            PolicyRule(
                id="meal_limit",
                text=(
                    "Meals must not exceed $50 per person. "
                    "Count main-course portions in line_items (each ramen, burger, entree, or main dish = 1 person; multiply by quantity). "
                    "Divide total_amount by that headcount before checking the $50 limit."
                ),
            ),
            PolicyRule(
                id="transport_limit",
                text="Transport expenses must not exceed $2000.",
            ),
            PolicyRule(
                id="accommodation_limit",
                text=(
                    "Accommodation must not exceed $300 per night. "
                    "Determine the per-night rate from line items directly (each dated room charge is one night). "
                    "If only a total is given, divide by the number of night line items."
                ),
            ),
            PolicyRule(
                id="equipment_limit",
                text="Equipment purchases must not exceed $1,000 without prior approval.",
            ),
        ]
    ),
)
