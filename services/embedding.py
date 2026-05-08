import logging

from config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, provider: str, model: str, api_key: str) -> None:
        self._provider = provider
        self._model = model
        self._api_key = api_key

    def embed_texts(self, texts: list[str]) -> list[list[float]] | None:
        """Embed a list of texts. Returns None on failure so callers can store without vectors."""
        if not texts or self._provider == "none":
            return None
        try:
            if self._provider == "google":
                return self._embed_with_google(texts)
            raise ValueError(f"Unknown embedding provider: {self._provider}")
        except Exception as exc:
            logger.warning("Embedding failed, storing without vectors: %s", exc)
            return None

    def _embed_with_google(self, texts: list[str]) -> list[list[float]]:
        from google import genai

        client = genai.Client(api_key=self._api_key)
        response = client.models.embed_content(model=self._model, contents=texts)
        return [e.values for e in response.embeddings]


def extract_embed_pairs(data: dict, embed_fields: list[str]) -> list[tuple[str, str]]:
    """
    Traverse data and return (field_path, text_value) pairs for the specified fields.
    Handles simple fields and arrays of strings or objects.
    """
    pairs: list[tuple[str, str]] = []
    for field in embed_fields:
        value = data.get(field)
        if isinstance(value, str) and value:
            pairs.append((field, value))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, str) and item:
                    pairs.append((f"{field}.{i}", item))
                elif isinstance(item, dict):
                    for k, v in item.items():
                        if isinstance(v, str) and v:
                            pairs.append((f"{field}.{i}.{k}", v))
    return pairs


def get_embedding_service() -> EmbeddingService:
    cfg = settings.get_embedding_config()
    api_key_map = {
        "google": settings.GEMINI_API_KEY,
    }
    return EmbeddingService(
        provider=cfg["provider"],
        model=cfg["model"],
        api_key=api_key_map.get(cfg["provider"], ""),
    )
