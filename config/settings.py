import os

from dotenv import load_dotenv

load_dotenv()

# API keys — sourced from .env only
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://automation:automation@localhost:5432/automation",
)


def get_agents() -> dict[str, dict]:
    from config.llm_config import CONFIG
    return {name: cfg.model_dump() for name, cfg in CONFIG.agents.items()}


def get_embedding_config() -> dict:
    from config.llm_config import CONFIG
    return CONFIG.embeddings.model_dump()
