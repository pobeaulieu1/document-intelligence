from models.schemas import AgentConfig, EmbeddingConfig, LLMConfig

CONFIG = LLMConfig(
    agents={
        "extraction": AgentConfig(
            provider="anthropic",
            model="claude-sonnet-4-6",
        ),
        "enrichment": AgentConfig(
            provider="anthropic",
            model="claude-sonnet-4-6",
        ),
        "validation": AgentConfig(
            provider="anthropic",
            model="claude-sonnet-4-6",
        ),
    },
    embeddings=EmbeddingConfig(
        provider="openai",
        model="text-embedding-3-small",
        dimensions=1536,
    ),
)
