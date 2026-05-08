from models.schemas import (
    SchemaConfig,
    Operator,
    Source,
    ValidationRule,
    ValidationRuleCondition,
    ValidationRules,
)

SCHEMA = SchemaConfig(
    key="receipt",
    name="Receipt",
    description="Extract structured data from retail and restaurant receipts",
    categorize_fields=["category"],
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
            "is_compliant": {
                "type": "boolean",
                "description": "Whether the expense satisfies all validation rules",
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
            ValidationRule(
                id="max_meal_amount",
                description="Meal receipts must not exceed $50 per person",
                source=Source.data,
                field="total_amount",
                operator=Operator.lte,
                value=50,
                condition=ValidationRuleCondition(
                    source=Source.enrichments,
                    field="category",
                    operator=Operator.eq,
                    value="meals",
                ),
                message="Meal expense exceeds the $50 per-person limit",
            ),
            ValidationRule(
                id="max_transport_amount",
                description="Transport receipts must not exceed $200 per trip",
                source=Source.data,
                field="total_amount",
                operator=Operator.lte,
                value=200,
                condition=ValidationRuleCondition(
                    source=Source.enrichments,
                    field="category",
                    operator=Operator.eq,
                    value="transport",
                ),
                message="Transport expense exceeds the $200 per-trip limit",
            ),
            ValidationRule(
                id="max_accommodation_amount",
                description="Accommodation must not exceed $300 per night",
                source=Source.data,
                field="total_amount",
                operator=Operator.lte,
                value=300,
                condition=ValidationRuleCondition(
                    source=Source.enrichments,
                    field="category",
                    operator=Operator.eq,
                    value="accommodation",
                ),
                message="Accommodation expense exceeds the $300 per-night limit",
            ),
            ValidationRule(
                id="max_equipment_amount",
                description="Equipment purchases must not exceed $1000 without pre-approval",
                source=Source.data,
                field="total_amount",
                operator=Operator.lte,
                value=1000,
                condition=ValidationRuleCondition(
                    source=Source.enrichments,
                    field="category",
                    operator=Operator.eq,
                    value="equipment",
                ),
                message="Equipment purchase exceeds the $1000 limit and requires pre-approval",
            ),
            ValidationRule(
                id="allowed_categories",
                description="Expense category must be one of the approved types",
                source=Source.enrichments,
                field="category",
                operator=Operator.in_,
                value=["meals", "transport", "accommodation", "equipment", "other"],
                message="Expense category is not in the approved list",
            ),
        ]
    ),
)
