"""
Dependências FastAPI: autenticação, DB, usuário atual.
Suporta Bearer header (REST) e query param ?token= (SSE/EventSource).
"""
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.supabase_client import supabase_admin

security = HTTPBearer(auto_error=False)


def _validate_token(token: str) -> UUID:
    """Valida JWT do Supabase e retorna o user_id."""
    try:
        response = supabase_admin().auth.get_user(token)
        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido ou expirado",
            )
        return UUID(str(response.user.id))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falha ao validar token",
        )


# UUID padrão quando auth está desabilitado (sem login)
_DEV_DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"


async def get_current_user_id(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
    token: Annotated[str | None, Query(description="JWT para SSE/EventSource")] = None,
) -> UUID:
    """
    Extrai e valida o JWT do Supabase.
    Aceita:
      - Header: Authorization: Bearer <token>  (REST endpoints)
      - Query param: ?token=<token>             (SSE/EventSource)
    Se não houver token e DEV_USER_ID estiver definido no .env (ou uso do padrão),
    retorna esse user_id (modo sem login).
    """
    if credentials and credentials.credentials:
        return _validate_token(credentials.credentials)
    if token:
        return _validate_token(token)
    # Modo sem login: usar usuário dev
    from app.config import settings
    dev_id = getattr(settings, "dev_user_id", "") or _DEV_DEFAULT_USER_ID
    if dev_id.strip():
        try:
            return UUID(dev_id.strip())
        except ValueError:
            pass
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de autenticação ausente",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_user_id(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
    token: Annotated[str | None, Query()] = None,
) -> UUID | None:
    """Retorna o user_id se token válido; None caso contrário."""
    try:
        return await get_current_user_id(request, credentials, token)
    except HTTPException:
        return None


async def get_current_user_profile(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
):
    """Busca o perfil do usuário em public.profiles."""
    client = supabase_admin()
    r = client.table("profiles").select("*").eq("id", str(user_id)).execute()
    if not r.data or len(r.data) == 0:
        return {"id": str(user_id), "full_name": None, "role": None, "avatar_url": None}
    return r.data[0]
