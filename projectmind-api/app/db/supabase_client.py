"""
Cliente Supabase singleton para a aplicação.
"""
from supabase import create_client, Client
from app.config import settings


def get_supabase_client() -> Client:
    """Retorna o cliente Supabase com anon key (para uso com RLS)."""
    return create_client(settings.supabase_url, settings.supabase_anon_key)


def _admin_key() -> str:
    """Chave para cliente admin: SERVICE_ROLE_KEY > SUPABASE_KEY (alias) > anon_key."""
    return (
        settings.supabase_service_role_key
        or getattr(settings, "supabase_key", "")
        or settings.supabase_anon_key
    )


def get_supabase_admin_client() -> Client:
    """Retorna o cliente Supabase com service_role (bypass RLS para operações server-side)."""
    return create_client(settings.supabase_url, _admin_key())


# Singletons para injeção
_supabase: Client | None = None
_supabase_admin: Client | None = None


def init_supabase() -> None:
    global _supabase, _supabase_admin
    admin_key = _admin_key()
    anon = settings.supabase_anon_key
    if settings.supabase_url and (anon or admin_key):
        _supabase = create_client(settings.supabase_url, anon or admin_key)
        _supabase_admin = create_client(settings.supabase_url, admin_key)


def supabase() -> Client:
    if _supabase is None:
        init_supabase()
    return _supabase  # type: ignore


def supabase_admin() -> Client:
    if _supabase_admin is None:
        init_supabase()
    return _supabase_admin  # type: ignore
