"""
Rotas de autenticação via Supabase Auth.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.api.deps import get_current_user_id, get_current_user_profile
from app.db.supabase_client import supabase_admin

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str | None = None


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginBody):
    """Login com email/senha via Supabase Auth."""
    try:
        response = supabase_admin().auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        ) from e
    if not response.user or not response.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falha no login",
        )
    return LoginResponse(
        access_token=response.session.access_token,
        user_id=str(response.user.id),
        email=response.user.email,
    )


class LogoutBody(BaseModel):
    """Opcional: enviar token para invalidar no server (Supabase não invalida por padrão)."""
    pass


@router.post("/logout")
async def logout():
    """Logout (client deve descartar o token)."""
    return {"message": "Faça logout no client descartando o token."}


@router.get("/me")
async def me(
    user_id: UUID = Depends(get_current_user_id),
    profile=Depends(get_current_user_profile),
):
    """Retorna o perfil do usuário autenticado."""
    return {
        "id": str(user_id),
        **profile,
    }
