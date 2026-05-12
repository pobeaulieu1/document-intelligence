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


def _get_config():
    from config.llm_config import CONFIG
    return CONFIG


def get_agent_config(agent_name: str) -> dict:
    """Return {"provider": "...", "model": "..."} for the given agent."""
    agents = _get_config().agents
    if agent_name not in agents:
        raise KeyError(f"No config for agent '{agent_name}' in llm_config.py")
    return agents[agent_name].model_dump()


def get_agents() -> dict[str, dict]:
    """Return the full agent → config mapping."""
    return {name: cfg.model_dump() for name, cfg in _get_config().agents.items()}


def get_embedding_config() -> dict:
    """Return {"provider": "...", "model": "...", "dimensions": N}."""
    return _get_config().embeddings.model_dump()
