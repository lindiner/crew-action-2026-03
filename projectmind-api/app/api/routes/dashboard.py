"""
Painel de gestão: snapshot atual, histórico e refresh com orchestration_mode.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, BackgroundTasks

from app.api.deps import get_current_user_id
from app.api.routes.projects import _ensure_project_access
from app.db.supabase_client import supabase_admin

router = APIRouter(tags=["dashboard"])


def _get_project_context_and_mode(client, project_id: str) -> tuple[str, str]:
    """Retorna (context, orchestration_mode) do projeto."""
    proj = client.table("projects").select("context_summary, orchestration_mode").eq("id", project_id).execute()
    context = ""
    mode = "hierarchical"
    if proj.data and proj.data[0]:
        context = proj.data[0].get("context_summary") or ""
        mode = proj.data[0].get("orchestration_mode") or "hierarchical"
    return context, mode


async def _refresh_dashboard_task(project_id: str):
    """Background: executa crew com mode correto e gera novo snapshot."""
    from app.agents.crew_manager import ProjectMindCrew

    client = supabase_admin()
    team_r = client.table("agent_teams").select("agents").eq("project_id", project_id).order("created_at", desc=True).limit(1).execute()
    active = []
    if team_r.data and team_r.data[0].get("agents"):
        active = [a["agent_type"] for a in team_r.data[0]["agents"] if a.get("active")]
    if not active:
        active = [
            "orchestrator", "risk_agent", "scope_agent", "schedule_agent",
            "stakeholder_agent", "comms_agent", "budget_agent", "blocker_agent", "kpi_agent",
            "quality_agent", "resource_agent", "change_agent", "docs_agent",
        ]

    context, mode = _get_project_context_and_mode(client, project_id)

    # Enriquecer com últimas ingestões
    ing = client.table("ingestions").select("parsed_summary, raw_content").eq("project_id", project_id).eq("status", "done").order("created_at", desc=True).limit(3).execute()
    if ing.data:
        for i in ing.data:
            context += "\n" + (i.get("parsed_summary") or i.get("raw_content", "")[:1500])

    if not context.strip():
        context = "Sem contexto ainda."

    crew = ProjectMindCrew(
        project_id=project_id,
        active_agents=active,
        context=context,
        orchestration_mode=mode,
    )
    result = await crew.run_analysis()
    if result:
        client.table("dashboard_snapshots").insert({
            "project_id": project_id,
            "health": result.get("health", "green"),
            "risks": result.get("risks", []),
            "actions": result.get("actions", []),
            "timeline": result.get("timeline", {}),
            "stakeholders": result.get("stakeholders", []),
            "kpis": result.get("kpis", []),
            "next_steps": result.get("next_steps", []),
            "generated_by_agents": result.get("generated_by_agents", []),
        }).execute()


@router.get("/projects/{project_id}/dashboard")
async def get_dashboard(
    project_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Último snapshot do painel de gestão."""
    _ensure_project_access(project_id, user_id)
    r = (
        supabase_admin()
        .table("dashboard_snapshots")
        .select("*")
        .eq("project_id", str(project_id))
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not r.data or len(r.data) == 0:
        return {
            "health": "green",
            "risks": [],
            "actions": [],
            "timeline": {},
            "stakeholders": [],
            "kpis": [],
            "next_steps": [],
            "generated_by_agents": [],
            "created_at": None,
        }
    return r.data[0]


@router.get("/projects/{project_id}/dashboard/history")
async def get_dashboard_history(
    project_id: UUID,
    limit: int = 20,
    user_id: UUID = Depends(get_current_user_id),
):
    """Histórico de snapshots do painel."""
    _ensure_project_access(project_id, user_id)
    r = (
        supabase_admin()
        .table("dashboard_snapshots")
        .select("id, health, created_at, generated_by_agents")
        .eq("project_id", str(project_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return {"snapshots": r.data or []}


@router.post("/projects/{project_id}/dashboard/refresh", status_code=202)
async def refresh_dashboard(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_current_user_id),
):
    """Força nova análise dos agentes e gera snapshot."""
    _ensure_project_access(project_id, user_id)
    background_tasks.add_task(_refresh_dashboard_task, str(project_id))
    return {"message": "Atualização do painel em andamento"}
