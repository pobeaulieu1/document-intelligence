"""resize embedding vector from 768 to 1536 for OpenAI text-embedding-3-small

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-12
"""
from typing import Sequence, Union

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM extraction_embeddings")
    op.alter_column(
        "extraction_embeddings",
        "embedding",
        type_=Vector(1536),
        existing_type=Vector(768),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.execute("DELETE FROM extraction_embeddings")
    op.alter_column(
        "extraction_embeddings",
        "embedding",
        type_=Vector(768),
        existing_type=Vector(1536),
        existing_nullable=True,
    )
