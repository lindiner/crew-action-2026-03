"""
Configuração do LLM para CrewAI: uma única entrada (CREWAI_* ou env).
Padrão: OpenRouter (CREWAI_API_KEY = chave OpenRouter, CREWAI_MODEL = openrouter/...).
"""
import os

from crewai import LLM

from app.config import settings

# Default: OpenRouter (Gemini via OpenRouter; não exige google-genai)
DEFAULT_MODEL = "openrouter/google/gemini-2.0-flash"


def get_crew_llm() -> LLM:
    """
    Retorna o LLM configurado para os agentes CrewAI.
    OpenRouter (padrão): CREWAI_API_KEY = chave OpenRouter, CREWAI_MODEL = openrouter/...
    """
    model = (
        getattr(settings, "crewai_model", None) or os.environ.get("CREWAI_MODEL") or DEFAULT_MODEL
    )
    model = model.strip() if model else DEFAULT_MODEL
    model_lower = model.lower()

    key = (
        getattr(settings, "crewai_api_key", "") or os.environ.get("CREWAI_API_KEY", "")
    ).strip()
    if not key and "gemini" in model_lower and not model_lower.startswith("openrouter/"):
        key = os.environ.get("GOOGLE_API_KEY", "").strip() or os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise ValueError(
            "Defina CREWAI_API_KEY no .env (chave OpenRouter em https://openrouter.ai/keys)."
        )

    # OpenRouter: modelo openrouter/... e base_url
    if model_lower.startswith("openrouter/"):
        return LLM(model=model, base_url="https://openrouter.ai/api/v1", api_key=key, temperature=0)

    # Gemini (provedor nativo): exige google-genai no mesmo ambiente
    if "gemini" in model_lower:
        try:
            import google.genai  # noqa: F401
        except ImportError:
            raise ValueError(
                "Modelo Gemini exige o pacote google-genai. "
                "Rode com o venv do projeto: .venv/bin/uvicorn app.main:app --reload --port 8000"
            )
        return LLM(model=model, api_key=key, temperature=0)

    # Demais provedores (OpenAI, Anthropic, etc.): mesmo formato da plataforma
    return LLM(model=model, api_key=key, temperature=0)
