"""rename categorize_fields to enrichment_fields

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-08
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("extraction_schemas", "categorize_fields", new_column_name="enrichment_fields")


def downgrade() -> None:
    op.alter_column("extraction_schemas", "enrichment_fields", new_column_name="categorize_fields")
