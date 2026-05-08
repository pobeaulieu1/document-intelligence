from fastapi import APIRouter

from config.llm_config import CONFIG
from models.schemas import LLMConfig

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/llm", response_model=LLMConfig)
def get_llm_config() -> LLMConfig:
    return CONFIG
