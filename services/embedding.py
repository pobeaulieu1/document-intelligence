import logging

from langchain_openai import OpenAIEmbeddings

from config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, provider: str, model: str, api_key: str, dimensions: int = 1536) -> None:
        self._provider = provider
        # LangChain's OpenAIEmbeddings wraps the OpenAI embeddings API.
        # embed_documents() returns list[list[float]] — one vector per input text.
        if provider == "openai":
            self._embedder = OpenAIEmbeddings(model=model, api_key=api_key, dimensions=dimensions)
        elif provider == "google":
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            self._embedder = GoogleGenerativeAIEmbeddings(model=model, google_api_key=api_key)
        else:
            self._embedder = None

    def embed_texts(self, texts: list[str]) -> list[list[float]] | None:
        if not texts or self._provider == "none" or self._embedder is None:
            return None
        try:
            return self._embedder.embed_documents(texts)
        except Exception as exc:
            logger.warning("Embedding failed, storing without vectors: %s", exc)
            return None


def extract_embed_pairs(data: dict, embed_fields: list[str]) -> list[tuple[str, str]]:
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
        "openai": settings.OPENAI_API_KEY,
    }
    return EmbeddingService(
        provider=cfg["provider"],
        model=cfg["model"],
        api_key=api_key_map.get(cfg["provider"], ""),
        dimensions=cfg.get("dimensions", 1536),
    )
