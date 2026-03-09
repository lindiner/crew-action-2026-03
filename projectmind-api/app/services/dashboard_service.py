"""
Composição do painel a partir de snapshots e dados do projeto.
"""
from uuid import UUID
from app.db.supabase_client import supabase_admin


class DashboardService:
    @staticmethod
    def get_latest_snapshot(project_id: UUID) -> dict | None:
        r = (
            supabase_admin()
            .table("dashboard_snapshots")
            .select("*")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if r.data and len(r.data) > 0:
            return r.data[0]
        return None

    @staticmethod
    def get_snapshot_history(project_id: UUID, limit: int = 20) -> list:
        r = (
            supabase_admin()
            .table("dashboard_snapshots")
            .select("id, health, created_at, generated_by_agents")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return r.data or []
