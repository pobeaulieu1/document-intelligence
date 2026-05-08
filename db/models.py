import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, LargeBinary, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, deferred, mapped_column, relationship

from config import settings


class Base(DeclarativeBase):
    pass


_embedding_dims: int = settings.get_embedding_config()["dimensions"]


class ExtractionSchemaORM(Base):
    __tablename__ = "extraction_schemas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    tool_schema: Mapped[dict] = mapped_column(JSONB, nullable=False)
    enrichments_schema: Mapped[dict | None] = mapped_column(JSONB)
    system_prompt: Mapped[str | None] = mapped_column(Text)
    embed_fields: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    # Fields from enrichments_schema that Agent 2 fills via LLM (e.g. ["category"]).
    # All other enrichment fields are computed deterministically by the validation engine.
    enrichment_fields: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    # Validation rules evaluated after extraction. Editable at runtime via the API.
    validation_rules: Mapped[dict | None] = mapped_column(JSONB)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    extractions: Mapped[list["ExtractionORM"]] = relationship(
        back_populates="schema", cascade="all, delete-orphan"
    )


class ExtractionORM(Base):
    __tablename__ = "extractions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schema_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extraction_schemas.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_hash: Mapped[str | None] = mapped_column(String(64))
    file_name: Mapped[str | None] = mapped_column(Text)
    file_content_type: Mapped[str | None] = mapped_column(Text)
    # deferred: excluded from default SELECT — only loaded when explicitly requested
    file_data: Mapped[bytes | None] = deferred(mapped_column(LargeBinary))
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    enrichments: Mapped[dict | None] = mapped_column(JSONB)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=0.95)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    schema: Mapped["ExtractionSchemaORM"] = relationship(back_populates="extractions")
    embeddings: Mapped[list["ExtractionEmbeddingORM"]] = relationship(
        back_populates="extraction", cascade="all, delete-orphan"
    )


class ExtractionEmbeddingORM(Base):
    __tablename__ = "extraction_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    extraction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extractions.id", ondelete="CASCADE"),
        nullable=False,
    )
    field_path: Mapped[str] = mapped_column(Text, nullable=False)
    field_value: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(_embedding_dims), nullable=True)

    extraction: Mapped["ExtractionORM"] = relationship(back_populates="embeddings")
