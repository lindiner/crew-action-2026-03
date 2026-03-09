"""
Gerenciamento do time de agentes por projeto, catálogo e sugestão por IA.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status

from app.api.deps import get_current_user_id
from app.api.routes.projects import _ensure_project_access
from app.db.supabase_client import supabase_admin
from app.models.agent_run import AgentTeamConfig, AgentTeamUpdate, SuggestTeamRequest

router = APIRouter(tags=["agents"])

AGENT_CATALOG = [
    {
        "agent_type": "orchestrator",
        "name": "Orquestrador",
        "description": "Coordena o time e distribui tarefas para agentes especializados.",
        "role": "Orquestrador de Projetos",
        "domain": "gestão",
    },
    {
        "agent_type": "risk_agent",
        "name": "Agente de Riscos",
        "description": "Identifica e analisa riscos do projeto; sugere mitigações e planos de contingência.",
        "role": "Analista de Riscos",
        "domain": "riscos",
    },
    {
        "agent_type": "scope_agent",
        "name": "Agente de Escopo",
        "description": "Mantém o escopo, identifica scope creep e garante alinhamento com os objetivos.",
        "role": "Gerente de Escopo",
        "domain": "escopo",
    },
    {
        "agent_type": "schedule_agent",
        "name": "Agente de Cronograma",
        "description": "Analisa cronograma, milestones, dependências e identifica atrasos.",
        "role": "Planejador de Cronograma",
        "domain": "cronograma",
    },
    {
        "agent_type": "stakeholder_agent",
        "name": "Agente de Stakeholders",
        "description": "Mapeia e analisa stakeholders, sentimento e estratégia de comunicação.",
        "role": "Analista de Stakeholders",
        "domain": "stakeholders",
    },
    {
        "agent_type": "comms_agent",
        "name": "Agente de Comunicação",
        "description": "Consolida outputs dos agentes e formata comunicados e status reports.",
        "role": "Comunicação do Projeto",
        "domain": "comunicação",
    },
    {
        "agent_type": "budget_agent",
        "name": "Agente de Custos e Orçamento",
        "description": "Analisa custos, orçamento, burn rate e ROI; alertas de estouro e projeções.",
        "role": "Analista de Custos",
        "domain": "custos",
    },
    {
        "agent_type": "blocker_agent",
        "name": "Agente de Impedimentos",
        "description": "Identifica impedimentos ativos, dependências externas e gargalos do time.",
        "role": "Analista de Impedimentos",
        "domain": "impedimentos",
    },
    {
        "agent_type": "kpi_agent",
        "name": "Agente de KPIs e Métricas",
        "description": "Extrai e acompanha KPIs de progresso, prazo, qualidade e entregáveis.",
        "role": "Analista de KPIs",
        "domain": "métricas",
    },
    {
        "agent_type": "quality_agent",
        "name": "Agente de Qualidade",
        "description": "Identifica critérios de aceite, débito técnico, testes e não-conformidades.",
        "role": "Analista de Qualidade",
        "domain": "qualidade",
    },
    {
        "agent_type": "resource_agent",
        "name": "Agente de Recursos e Capacidade",
        "description": "Analisa alocação, capacidade da equipe, sobrecarga e skills necessários.",
        "role": "Analista de Recursos",
        "domain": "recursos",
    },
    {
        "agent_type": "change_agent",
        "name": "Agente de Mudança e Impacto",
        "description": "Analisa pedidos de mudança e impacto em escopo, cronograma e custo.",
        "role": "Analista de Mudança",
        "domain": "mudança",
    },
    {
        "agent_type": "docs_agent",
        "name": "Agente de Documentação e Status",
        "description": "Identifica documentação faltante e sugere artefatos e status reports.",
        "role": "Analista de Documentação",
        "domain": "documentação",
    },
]


@router.get("/agents/catalog")
async def get_agents_catalog(user_id: UUID = Depends(get_current_user_id)):
    """Lista todos os agentes disponíveis: nativos + customizados (próprios e públicos)."""
    native = [{**a, "is_custom": False} for a in AGENT_CATALOG]
    try:
        client = supabase_admin()
        mine = client.table("custom_agents").select("*").eq("created_by", str(user_id)).execute()
        mine_data = mine.data or []
        mine_ids = {a["id"] for a in mine_data}
        others = client.table("custom_agents").select("*").eq("is_public", True).execute()
        others_data = [a for a in (others.data or []) if a["id"] not in mine_ids]
        custom = [
            {
                "agent_type": f"custom:{a['id']}",
                "name": a["name"],
                "description": a["description"] or "",
                "role": a["role"],
                "domain": a.get("domain", "custom"),
                "is_custom": True,
                "is_public": a["is_public"],
                "created_by": a["created_by"],
                "is_mine": a["created_by"] == str(user_id),
            }
            for a in mine_data + others_data
        ]
        return {"agents": native + custom}
    except Exception:
        return {"agents": native}


@router.get("/projects/{project_id}/team")
async def get_project_team(
    project_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Time atual de agentes do projeto. Retorna time padrão se o banco falhar."""
    try:
        _ensure_project_access(project_id, user_id)
    except Exception:
        return {
            "agents": [
                {"agent_type": a["agent_type"], "active": True, "config": {}}
                for a in AGENT_CATALOG
            ],
            "suggested_by_ai": False,
        }
    try:
        r = (
            supabase_admin()
            .table("agent_teams")
            .select("*")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not r.data or len(r.data) == 0:
            return {
                "agents": [
                    {"agent_type": a["agent_type"], "active": True, "config": {}}
                    for a in AGENT_CATALOG
                ],
                "suggested_by_ai": False,
            }
        row = r.data[0]
        return {"agents": row["agents"], "suggested_by_ai": row.get("suggested_by_ai", False)}
    except Exception:
        return {
            "agents": [
                {"agent_type": a["agent_type"], "active": True, "config": {}}
                for a in AGENT_CATALOG
            ],
            "suggested_by_ai": False,
        }


@router.post("/projects/{project_id}/team")
async def update_project_team(
    project_id: UUID,
    body: AgentTeamUpdate,
    user_id: UUID = Depends(get_current_user_id),
):
    """Define/atualiza o time de agentes do projeto."""
    _ensure_project_access(project_id, user_id)
    native_types = {a["agent_type"] for a in AGENT_CATALOG}
    for ag in body.agents:
        if ag.agent_type in native_types:
            continue
        # Aceita agentes customizados no formato "custom:<uuid>"
        if ag.agent_type.startswith("custom:"):
            agent_uuid = ag.agent_type.split(":", 1)[1]
            r = supabase_admin().table("custom_agents").select("id, is_public, created_by").eq("id", agent_uuid).execute()
            if not r.data:
                raise HTTPException(400, detail=f"Agente customizado não encontrado: {ag.agent_type}")
            ca = r.data[0]
            if not ca["is_public"] and ca["created_by"] != str(user_id):
                raise HTTPException(403, detail=f"Sem acesso ao agente: {ag.agent_type}")
            continue
        raise HTTPException(400, detail=f"agent_type inválido: {ag.agent_type}")
    payload = {
        "project_id": str(project_id),
        "agents": [a.model_dump() for a in body.agents],
        "suggested_by_ai": False,
    }
    r = supabase_admin().table("agent_teams").insert(payload).execute()
    if not r.data or len(r.data) == 0:
        raise HTTPException(500, detail="Falha ao salvar time")
    return r.data[0]


async def _run_suggest_team(project_id: str, context_override: str | None) -> list[dict]:
    """Executa Orquestrador (agente de análise de contexto) e retorna lista de agentes sugeridos."""
    from app.agents.crew_manager import ProjectMindCrew

    context = ""
    mode = "hierarchical"
    if context_override and context_override.strip():
        context = context_override[:12000]
    else:
        try:
            client = supabase_admin()
            proj = client.table("projects").select("context_summary, orchestration_mode").eq("id", project_id).execute()
            if proj.data and proj.data[0]:
                context = proj.data[0].get("context_summary") or ""
                mode = proj.data[0].get("orchestration_mode") or "hierarchical"
            ing = client.table("ingestions").select("parsed_summary, raw_content").eq("project_id", project_id).eq("status", "done").order("created_at", desc=True).limit(3).execute()
            if ing.data:
                for i in ing.data:
                    context += "\n" + (i.get("parsed_summary") or i.get("raw_content", "")[:1500])
        except Exception:
            pass
    if not context.strip():
        context = "Sem contexto disponível. Sugira um time completo como padrão."

    crew = ProjectMindCrew(
        project_id=project_id,
        active_agents=["orchestrator"],
        context=context,
        orchestration_mode=mode,
    )
    suggestion = await crew.suggest_team()
    suggested = suggestion.get("suggested_agents", [])

    agents_payload = []
    suggested_map = {a["agent_type"]: a for a in suggested}
    for catalog_agent in AGENT_CATALOG:
        atype = catalog_agent["agent_type"]
        if atype in suggested_map:
            agents_payload.append({
                "agent_type": atype,
                "active": suggested_map[atype].get("active", True),
                "config": {"justification": suggested_map[atype].get("justification", "")},
            })
        else:
            agents_payload.append({"agent_type": atype, "active": False, "config": {}})
    return agents_payload


async def _suggest_team_task(project_id: str, context_override: str | None = None):
    """Background: executa Orquestrador para sugerir time e salva no banco."""
    agents_payload = await _run_suggest_team(project_id, context_override)
    try:
        supabase_admin().table("agent_teams").insert({
            "project_id": project_id,
            "agents": agents_payload,
            "suggested_by_ai": True,
        }).execute()
    except Exception:
        pass


@router.post("/projects/{project_id}/team/suggest")
async def suggest_team(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    body: SuggestTeamRequest | None = None,
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Orquestrador (agente de análise de contexto) analisa o projeto e sugere o time ideal de agentes.
    Se body.context for enviado: executa de forma síncrona e retorna 200 com os agentes sugeridos.
    Caso contrário: 202 e poll GET /team.
    """
    from fastapi.responses import JSONResponse

    _ensure_project_access(project_id, user_id)
    context_override = body.context if body and body.context else None

    if context_override and context_override.strip():
        # Fluxo síncrono: agente de análise de contexto roda agora e devolve a sugestão
        try:
            agents_payload = await _run_suggest_team(str(project_id), context_override)
        except Exception as e:
            err = str(e).lower()
            if "authentication" in err or "401" in err or "openrouter" in err or "user not found" in err:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="OpenRouter: chave inválida ou conta inativa. Verifique OPENROUTER_API_KEY em openrouter.ai e no .env",
                )
            raise
        try:
            supabase_admin().table("agent_teams").insert({
                "project_id": str(project_id),
                "agents": agents_payload,
                "suggested_by_ai": True,
            }).execute()
        except Exception:
            pass
        return JSONResponse(
            status_code=200,
            content={"agents": agents_payload, "suggested_by_ai": True},
        )

    background_tasks.add_task(_suggest_team_task, str(project_id), None)
    return JSONResponse(
        status_code=202,
        content={"message": "Sugestão de time em andamento. Consulte GET /team em instantes."},
    )
