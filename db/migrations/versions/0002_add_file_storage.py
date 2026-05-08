"""add file_data and file_content_type to extractions

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("extractions", sa.Column("file_content_type", sa.Text(), nullable=True))
    # file_data is deferred in the ORM (not loaded on every query) — BYTEA stores the raw upload
    op.add_column("extractions", sa.Column("file_data", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column("extractions", "file_data")
    op.drop_column("extractions", "file_content_type")
