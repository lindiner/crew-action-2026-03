"""
Status e conexão de integrações (Asana, Slack, Gmail).
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_user_id
from app.db.supabase_client import supabase_admin

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("")
async def list_integrations_status(user_id=Depends(get_current_user_id)):
    """Status de cada integração (conectado ou não). Por ora, tokens globais."""
    from app.config import settings
    return {
        "asana": {"connected": bool(settings.asana_access_token)},
        "slack": {"connected": bool(settings.slack_bot_token)},
        "gmail": {"connected": False, "message": "OAuth por usuário em breve"},
    }


class ConnectBody(BaseModel):
    token: str


@router.post("/asana/connect")
async def connect_asana(
    body: ConnectBody,
    user_id=Depends(get_current_user_id),
):
    """Salva token Asana (MVP: por usuário em tabela integrations ou env)."""
    # MVP: poderia salvar em tabela user_integrations (user_id, provider, token_encrypted)
    raise HTTPException(
        501,
        detail="Salvar token por usuário será implementado (tabela user_integrations). Use ASANA_ACCESS_TOKEN no .env para teste.",
    )


@router.post("/slack/connect")
async def connect_slack(
    body: ConnectBody,
    user_id=Depends(get_current_user_id),
):
    """Salva token Slack."""
    raise HTTPException(
        501,
        detail="Salvar token por usuário será implementado. Use SLACK_BOT_TOKEN no .env para teste.",
    )
