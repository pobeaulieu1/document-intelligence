from config import settings
from .anthropic_provider import AnthropicProvider
from .base import LLMProvider
from .gemini_provider import GeminiProvider

_REGISTRY = {
    "anthropic": lambda model: AnthropicProvider(api_key=settings.ANTHROPIC_API_KEY, model=model),
    "gemini": lambda model: GeminiProvider(api_key=settings.GEMINI_API_KEY, model=model),
}


def get_provider(agent_name: str) -> LLMProvider:
    """Return the configured LLMProvider instance for the given agent."""
    cfg = settings.get_agent_config(agent_name)
    provider_name = cfg["provider"]
    model = cfg["model"]

    factory = _REGISTRY.get(provider_name)
    if factory is None:
        raise ValueError(
            f"Unknown provider '{provider_name}'. "
            f"Supported: {', '.join(_REGISTRY)}"
        )

    return factory(model)
