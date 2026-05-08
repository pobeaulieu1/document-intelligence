from models.schemas import AgentConfig, EmbeddingConfig, LLMConfig

CONFIG = LLMConfig(
    agents={
        "extraction": AgentConfig(
            provider="anthropic",
            model="claude-sonnet-4-6",
        ),
        "enrichment": AgentConfig(
            provider="anthropic",
            model="claude-haiku-4-5-20251001",
        ),
    },
    embeddings=EmbeddingConfig(
        provider="none",
        model="",
        dimensions=768,
    ),
)
