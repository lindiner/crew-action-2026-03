"""
CRUD de projetos.
"""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user_id
from app.db.supabase_client import supabase_admin
from app.models.project import ProjectCreate, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


def _ensure_project_access(project_id: UUID, user_id: UUID) -> dict:
    """Garante que o usuário tem acesso ao projeto; retorna o projeto."""
    r = (
        supabase_admin()
        .table("projects")
        .select("*")
        .eq("id", str(project_id))
        .execute()
    )
    if not r.data or len(r.data) == 0:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    project = r.data[0]
    if project["owner_id"] != str(user_id):
        m = (
            supabase_admin()
            .table("project_members")
            .select("user_id")
            .eq("project_id", str(project_id))
            .eq("user_id", str(user_id))
            .execute()
        )
        if not m.data or len(m.data) == 0:
            raise HTTPException(status_code=403, detail="Sem acesso ao projeto")
    return project


def _build_project_payload(body: ProjectCreate | ProjectUpdate) -> dict:
    """Constrói payload para insert/update, unificando objective/description."""
    data = body.model_dump(exclude_unset=True)
    # objective tem precedência; description é alias legado
    if "objective" not in data and "description" in data:
        data["objective"] = data.pop("description")
    elif "objective" in data:
        data.pop("description", None)
    return data


@router.get("")
async def list_projects(user_id: UUID = Depends(get_current_user_id)):
    """Lista projetos do usuário (owner ou membro). Retorna lista vazia se Supabase falhar."""
    try:
        r = (
            supabase_admin()
            .table("projects")
            .select("*")
            .eq("owner_id", str(user_id))
            .order("updated_at", desc=True)
            .execute()
        )
        owned = r.data or []
        m = (
            supabase_admin()
            .table("project_members")
            .select("project_id")
            .eq("user_id", str(user_id))
            .execute()
        )
        member_ids = [x["project_id"] for x in (m.data or [])]
        if member_ids:
            r2 = (
                supabase_admin()
                .table("projects")
                .select("*")
                .in_("id", member_ids)
                .order("updated_at", desc=True)
                .execute()
            )
            other = [p for p in (r2.data or []) if p["id"] not in [x["id"] for x in owned]]
        else:
            other = []
        return {"projects": owned + other}
    except Exception:
        return {"projects": []}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    user_id: UUID = Depends(get_current_user_id),
):
    """Cria novo projeto."""
    data = _build_project_payload(body)
    data["owner_id"] = str(user_id)
    try:
        r = supabase_admin().table("projects").insert(data).execute()
    except Exception as e:
        err_msg = str(e).strip() or e.__class__.__name__
        # Mensagem amigável para erros conhecidos
        if "foreign key" in err_msg.lower() or "violates foreign key" in err_msg.lower():
            detail = (
                "owner_id não existe em auth/users. Com modo sem login: crie um usuário em "
                "Supabase (Authentication → Users → Add user) e defina DEV_USER_ID no .env com o UUID desse usuário. "
                "Ou ative RLS e use um token JWT válido."
            )
        elif "401" in err_msg or "invalid" in err_msg.lower() or "api key" in err_msg.lower():
            detail = "Chave Supabase inválida. Verifique SUPABASE_SERVICE_ROLE_KEY (ou SUPABASE_KEY) no .env."
        else:
            detail = f"Banco: {err_msg[:200]}"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )
    if not r.data or len(r.data) == 0:
        raise HTTPException(status_code=500, detail="Falha ao criar projeto")
    return r.data[0]


@router.get("/{project_id}")
async def get_project(
    project_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Detalhes do projeto."""
    project = _ensure_project_access(project_id, user_id)
    return project


@router.patch("/{project_id}")
async def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    user_id: UUID = Depends(get_current_user_id),
):
    """Atualiza projeto."""
    _ensure_project_access(project_id, user_id)
    payload = _build_project_payload(body)
    if not payload:
        return await get_project(project_id, user_id)
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    r = (
        supabase_admin()
        .table("projects")
        .update(payload)
        .eq("id", str(project_id))
        .execute()
    )
    if not r.data or len(r.data) == 0:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return r.data[0]


@router.delete("/{project_id}")
async def delete_project(
    project_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Arquiva projeto (soft delete: status = archived)."""
    _ensure_project_access(project_id, user_id)
    supabase_admin().table("projects").update({
        "status": "archived",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", str(project_id)).execute()
    return {"message": "Projeto arquivado"}
