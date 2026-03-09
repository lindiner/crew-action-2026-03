"""
Ingestão de contexto (transcrições, e-mails, documentos).
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from app.api.deps import get_current_user_id
from app.api.routes.projects import _ensure_project_access
from app.db.supabase_client import supabase_admin
from app.models.ingestion import IngestionCreate

router = APIRouter(tags=["ingestion"])


def _get_project_mode(client, project_id: str) -> str:
    """Busca orchestration_mode do projeto; default hierarchical."""
    try:
        r = client.table("projects").select("orchestration_mode").eq("id", project_id).execute()
        if r.data and r.data[0]:
            return r.data[0].get("orchestration_mode") or "hierarchical"
    except Exception:
        pass
    return "hierarchical"


async def _run_ingestion_pipeline(ingestion_id: str, project_id: str, body: IngestionCreate):
    """Background: processa ingestão (parse + embedding + crew + dashboard)."""
    from app.services.ingestion_service import IngestionService
    from app.agents.crew_manager import ProjectMindCrew

    client = supabase_admin()
    try:
        client.table("ingestions").update({"status": "processing"}).eq("id", ingestion_id).execute()
    except Exception:
        pass

    try:
        svc = IngestionService()
        if body.type == "transcript":
            parsed = await svc.parse_transcript(body.content)
        elif body.type == "email":
            parsed = await svc.parse_email_thread(body.content)
        else:
            parsed = await svc.parse_transcript(body.content)

        embedding: list[float] = []
        try:
            embedding = await svc.generate_embedding((parsed.summary or "") + " " + body.content[:2000])
        except Exception:
            pass

        update_payload: dict = {
            "parsed_summary": parsed.summary,
            "extracted_entities": parsed.model_dump(exclude={"summary"}),
            "status": "done",
        }
        if embedding:
            update_payload["embedding"] = embedding
        client.table("ingestions").update(update_payload).eq("id", ingestion_id).execute()

        # Atualizar context_summary do projeto com o novo resumo
        if parsed.summary:
            try:
                proj = client.table("projects").select("context_summary").eq("id", project_id).execute()
                existing = (proj.data and proj.data[0].get("context_summary")) or ""
                combined = (existing + "\n\n" + parsed.summary).strip()[-8000:]
                client.table("projects").update({"context_summary": combined}).eq("id", project_id).execute()
            except Exception:
                pass

        # Crew: análise e atualização do dashboard
        try:
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

            mode = _get_project_mode(client, project_id)
            context = parsed.summary or body.content[:4000]

            crew = ProjectMindCrew(
                project_id=project_id,
                active_agents=active,
                context=context,
                orchestration_mode=mode,
                ingestion_id=ingestion_id,
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
        except Exception:
            pass

    except Exception:
        try:
            client.table("ingestions").update({"status": "error"}).eq("id", ingestion_id).execute()
        except Exception:
            pass


@router.post("/projects/{project_id}/ingest", status_code=202)
async def create_ingestion(
    project_id: UUID,
    body: IngestionCreate,
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_current_user_id),
):
    """Cria registro de ingestão e dispara pipeline assíncrono."""
    _ensure_project_access(project_id, user_id)
    if body.type not in ("transcript", "email", "document"):
        raise HTTPException(400, detail="type deve ser transcript, email ou document")
    row = {
        "project_id": str(project_id),
        "type": body.type,
        "raw_content": body.content,
        "status": "pending",
    }
    r = supabase_admin().table("ingestions").insert(row).execute()
    if not r.data or len(r.data) == 0:
        raise HTTPException(500, detail="Falha ao criar ingestão")
    ingestion = r.data[0]
    background_tasks.add_task(
        _run_ingestion_pipeline,
        ingestion["id"],
        str(project_id),
        body,
    )
    return {"ingestion_id": ingestion["id"], "status": "processing"}


@router.get("/projects/{project_id}/ingest")
async def list_ingestions(
    project_id: UUID,
    limit: int = 20,
    user_id: UUID = Depends(get_current_user_id),
):
    """Lista ingestões do projeto com status."""
    _ensure_project_access(project_id, user_id)
    r = (
        supabase_admin()
        .table("ingestions")
        .select("id, type, status, parsed_summary, created_at")
        .eq("project_id", str(project_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return {"ingestions": r.data or []}


@router.get("/projects/{project_id}/ingest/{ingestion_id}")
async def get_ingestion_status(
    project_id: UUID,
    ingestion_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Status e resultado de uma ingestão específica."""
    _ensure_project_access(project_id, user_id)
    r = (
        supabase_admin()
        .table("ingestions")
        .select("*")
        .eq("id", str(ingestion_id))
        .eq("project_id", str(project_id))
        .execute()
    )
    if not r.data or len(r.data) == 0:
        raise HTTPException(404, detail="Ingestão não encontrada")
    return r.data[0]
