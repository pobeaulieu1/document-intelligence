"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-01-01 00:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "extraction_schemas",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("key", sa.String(), unique=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("tool_schema", postgresql.JSONB(), nullable=False),
        sa.Column("enrichments_schema", postgresql.JSONB()),
        sa.Column("system_prompt", sa.Text()),
        sa.Column("embed_fields", postgresql.ARRAY(sa.Text())),
        sa.Column("categorize_fields", postgresql.ARRAY(sa.Text())),
        sa.Column("validation_rules", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_extraction_schemas_key", "extraction_schemas", ["key"])

    op.create_table(
        "extractions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "schema_id",
            sa.UUID(),
            sa.ForeignKey("extraction_schemas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_hash", sa.String(64)),
        sa.Column("file_name", sa.Text()),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("enrichments", postgresql.JSONB()),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_extractions_schema_id", "extractions", ["schema_id"])

    op.create_table(
        "extraction_embeddings",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "extraction_id",
            sa.UUID(),
            sa.ForeignKey("extractions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_path", sa.Text(), nullable=False),
        sa.Column("field_value", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=True),
    )
    op.create_index(
        "ix_extraction_embeddings_extraction_id", "extraction_embeddings", ["extraction_id"]
    )


def downgrade() -> None:
    op.drop_table("extraction_embeddings")
    op.drop_table("extractions")
    op.drop_table("extraction_schemas")
