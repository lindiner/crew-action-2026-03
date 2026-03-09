"""
Chat com agentes: histórico e envio de mensagens; SSE para streaming.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
import asyncio
import json

from app.api.deps import get_current_user_id
from app.api.routes.projects import _ensure_project_access
from app.db.supabase_client import supabase_admin
from app.models.chat_message import ChatMessageCreate

router = APIRouter(tags=["chat"])


@router.get("/projects/{project_id}/chat")
async def get_chat_history(
    project_id: UUID,
    limit: int = 50,
    user_id: UUID = Depends(get_current_user_id),
):
    """Histórico de mensagens do chat."""
    _ensure_project_access(project_id, user_id)
    r = (
        supabase_admin()
        .table("chat_messages")
        .select("*")
        .eq("project_id", str(project_id))
        .order("created_at", desc=False)
        .limit(limit)
        .execute()
    )
    return {"messages": r.data or []}


@router.post("/projects/{project_id}/chat")
async def send_chat_message(
    project_id: UUID,
    body: ChatMessageCreate,
    user_id: UUID = Depends(get_current_user_id),
):
    """Envia mensagem e retorna resposta dos agentes (sem streaming)."""
    _ensure_project_access(project_id, user_id)
    client = supabase_admin()
    # Salvar mensagem do usuário
    user_msg = {
        "project_id": str(project_id),
        "sender_type": "user",
        "sender_id": str(user_id),
        "content": body.content,
        "structured_content": None,
    }
    client.table("chat_messages").insert(user_msg).execute()
    # Resposta do agente (sync para este endpoint)
    from app.agents.crew_manager import ProjectMindCrew
    team_r = client.table("agent_teams").select("agents").eq("project_id", str(project_id)).order("created_at", desc=True).limit(1).execute()
    active = []
    if team_r.data and team_r.data[0].get("agents"):
        active = [a["agent_type"] for a in team_r.data[0]["agents"] if a.get("active")]
    if not active:
        active = ["orchestrator", "comms_agent"]
    target = body.target_agent or "orchestrator"
    if target not in active:
        target = active[0] if active else "orchestrator"
    crew = ProjectMindCrew(project_id=str(project_id), active_agents=active, context=body.content)
    try:
        reply_text = await crew.chat(user_message=body.content, target_agent=target)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        err_msg = str(e).lower()
        if "401" in err_msg or "authenticationerror" in err_msg or "openrouter" in err_msg or "user not found" in err_msg:
            raise HTTPException(
                status_code=503,
                detail="Serviço de IA indisponível: chave inválida ou ausente. Configure CREWAI_API_KEY no .env.",
            ) from e
        if "400" in err_msg and ("api key not valid" in err_msg or "api_key_invalid" in err_msg or "invalid_argument" in err_msg):
            raise HTTPException(
                status_code=503,
                detail="Chave do Gemini inválida. Use uma API key do Google AI Studio em CREWAI_API_KEY ou GOOGLE_API_KEY no .env.",
            ) from e
        # Resposta vazia do LLM (rate limit, timeout ou instabilidade)
        if "none or empty" in err_msg or "invalid response from llm" in err_msg:
            raise HTTPException(
                status_code=503,
                detail="O modelo de IA não respondeu. Tente novamente em alguns segundos (pode ser limite de uso ou instabilidade).",
            ) from e
        raise
    agent_msg = {
        "project_id": str(project_id),
        "sender_type": "agent",
        "sender_id": target,
        "agent_type": target,
        "content": reply_text,
        "structured_content": None,
    }
    r = client.table("chat_messages").insert(agent_msg).execute()
    return {"message": agent_msg, "reply": reply_text}


async def _stream_agent_reply(project_id: str, user_id: str, content: str, target_agent: str | None):
    """Generator para SSE: envia chunks da resposta do agente."""
    from app.agents.crew_manager import ProjectMindCrew
    client = supabase_admin()
    team_r = client.table("agent_teams").select("agents").eq("project_id", project_id).order("created_at", desc=True).limit(1).execute()
    active = [a["agent_type"] for a in (team_r.data[0]["agents"] if team_r.data and team_r.data[0].get("agents") else []) if a.get("active")]
    if not active:
        active = ["orchestrator", "comms_agent"]
    target = target_agent or active[0]
    crew = ProjectMindCrew(project_id=project_id, active_agents=active, context=content)
    # Stream simulado: CrewAI pode não suportar streaming nativo; enviamos chunks quando disponíveis
    full_reply = await crew.chat(user_message=content, target_agent=target)
    # Enviar em um chunk ou em pedaços para efeito de streaming
    chunk_size = 80
    for i in range(0, len(full_reply), chunk_size):
        yield {"data": json.dumps({"content": full_reply[i : i + chunk_size], "done": False})}
        await asyncio.sleep(0.02)
    yield {"data": json.dumps({"content": "", "done": True})}
    # Persistir mensagens
    client.table("chat_messages").insert({
        "project_id": project_id,
        "sender_type": "user",
        "sender_id": user_id,
        "content": content,
    }).execute()
    client.table("chat_messages").insert({
        "project_id": project_id,
        "sender_type": "agent",
        "sender_id": target,
        "agent_type": target,
        "content": full_reply,
    }).execute()


@router.get("/projects/{project_id}/chat/stream")
async def chat_stream(
    project_id: UUID,
    q: str = "",
    target_agent: str | None = None,
    user_id: UUID = Depends(get_current_user_id),
):
    """SSE endpoint para streaming de respostas. Use query ?q=mensagem&target_agent=opcional."""
    _ensure_project_access(project_id, user_id)
    if not q.strip():
        raise HTTPException(400, detail="Query 'q' é obrigatória para o stream")
    return EventSourceResponse(
        _stream_agent_reply(str(project_id), str(user_id), q, target_agent)
    )
