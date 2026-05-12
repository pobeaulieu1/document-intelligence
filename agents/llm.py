from config.llm_config import CONFIG


def get_chat_model(agent_name: str):
    """Return a LangChain chat model for the given agent, driven by llm_config.py."""
    cfg = CONFIG.agents[agent_name]

    if cfg.provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=cfg.model, max_retries=6)

    if cfg.provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=cfg.model)

    if cfg.provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=cfg.model)

    raise ValueError(f"Unsupported provider '{cfg.provider}' for agent '{agent_name}'")
