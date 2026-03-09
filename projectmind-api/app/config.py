"""
Configuração da aplicação via pydantic-settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "ProjectMind AI"
    debug: bool = False
    environment: str = "development"

    # Supabase (SUPABASE_KEY no .env é aceito como alias de SUPABASE_SERVICE_ROLE_KEY)
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_key: str = ""  # alias: se service_role vazio, usa este (ex.: chave publishable no .env)


    # CrewAI: OpenRouter por padrão (chave em https://openrouter.ai/keys)
    crewai_api_key: str = ""
    crewai_model: str = "openrouter/google/gemini-2.0-flash"
    crewai_project_id: str = ""


    # Redis (fila assíncrona / Celery)
    redis_url: str = "redis://localhost:6379/0"

    # MCP / Integrações (tokens opcionais)
    asana_access_token: str = ""
    slack_bot_token: str = ""
    # Gmail via OAuth2 - client_id/secret em integrações por usuário

    # CORS (string separada por vírgulas no .env; use cors_origins_list no código)
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # JWT (Supabase usa seu próprio JWT; podemos validar com a mesma secret)
    jwt_algorithm: str = "HS256"

    # Modo sem login: quando não há token, usa este user_id (UUID). Deixe vazio para exigir login.
    dev_user_id: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()] or ["http://localhost:3000"]


settings = Settings()
