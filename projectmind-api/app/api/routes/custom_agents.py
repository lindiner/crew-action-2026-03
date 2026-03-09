"""
CRUD de agentes customizados.
Agentes podem ser privados (só do criador) ou públicos (qualquer usuário pode usar em seus projetos).
"""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user_id
from app.db.supabase_client import supabase_admin
from app.models.custom_agent import CustomAgentCreate, CustomAgentUpdate

router = APIRouter(prefix="/agents/custom", tags=["custom-agents"])


def _get_agent_or_404(agent_id: UUID) -> dict:
    r = (
        supabase_admin()
        .table("custom_agents")
        .select("*")
        .eq("id", str(agent_id))
        .execute()
    )
    if not r.data:
        raise HTTPException(status_code=404, detail="Agente não encontrado")
    return r.data[0]


def _ensure_owner(agent: dict, user_id: UUID) -> None:
    if agent["created_by"] != str(user_id):
        raise HTTPException(status_code=403, detail="Sem permissão para editar este agente")


@router.get("")
async def list_custom_agents(user_id: UUID = Depends(get_current_user_id)):
    """
    Lista agentes disponíveis para o usuário:
    - Seus próprios agentes (privados e públicos)
    - Agentes públicos de outros usuários
    """
    try:
        client = supabase_admin()
        mine = client.table("custom_agents").select("*").eq("created_by", str(user_id)).order("created_at", desc=True).execute()
        mine_data = mine.data or []
        mine_ids = {a["id"] for a in mine_data}
        others = client.table("custom_agents").select("*").eq("is_public", True).order("created_at", desc=True).execute()
        others_data = [a for a in (others.data or []) if a["id"] not in mine_ids]
        return {"my_agents": mine_data, "public_agents": others_data}
    except Exception:
        return {"my_agents": [], "public_agents": []}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_custom_agent(
    body: CustomAgentCreate,
    user_id: UUID = Depends(get_current_user_id),
):
    """Cria um novo agente customizado."""
    data = body.model_dump()
    data["created_by"] = str(user_id)
    r = supabase_admin().table("custom_agents").insert(data).execute()
    if not r.data:
        raise HTTPException(status_code=500, detail="Falha ao criar agente")
    return r.data[0]


@router.get("/{agent_id}")
async def get_custom_agent(
    agent_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Retorna detalhes de um agente (próprio ou público)."""
    agent = _get_agent_or_404(agent_id)
    if agent["created_by"] != str(user_id) and not agent["is_public"]:
        raise HTTPException(status_code=403, detail="Sem acesso a este agente")
    return agent


@router.patch("/{agent_id}")
async def update_custom_agent(
    agent_id: UUID,
    body: CustomAgentUpdate,
    user_id: UUID = Depends(get_current_user_id),
):
    """Atualiza um agente customizado (apenas o criador)."""
    agent = _get_agent_or_404(agent_id)
    _ensure_owner(agent, user_id)
    payload = body.model_dump(exclude_unset=True)
    if not payload:
        return agent
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    r = (
        supabase_admin()
        .table("custom_agents")
        .update(payload)
        .eq("id", str(agent_id))
        .execute()
    )
    if not r.data:
        raise HTTPException(status_code=500, detail="Falha ao atualizar agente")
    return r.data[0]


@router.post("/{agent_id}/publish", status_code=status.HTTP_200_OK)
async def publish_custom_agent(
    agent_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Torna o agente público para todos os usuários."""
    agent = _get_agent_or_404(agent_id)
    _ensure_owner(agent, user_id)
    r = (
        supabase_admin()
        .table("custom_agents")
        .update({"is_public": True, "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", str(agent_id))
        .execute()
    )
    return r.data[0] if r.data else agent


@router.post("/{agent_id}/unpublish", status_code=status.HTTP_200_OK)
async def unpublish_custom_agent(
    agent_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Torna o agente privado novamente."""
    agent = _get_agent_or_404(agent_id)
    _ensure_owner(agent, user_id)
    r = (
        supabase_admin()
        .table("custom_agents")
        .update({"is_public": False, "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", str(agent_id))
        .execute()
    )
    return r.data[0] if r.data else agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_agent(
    agent_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Remove um agente customizado (apenas o criador)."""
    agent = _get_agent_or_404(agent_id)
    _ensure_owner(agent, user_id)
    supabase_admin().table("custom_agents").delete().eq("id", str(agent_id)).execute()
