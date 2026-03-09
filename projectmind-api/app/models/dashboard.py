"""
Modelos para o painel de gestão (snapshots).
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class RiskItem(BaseModel):
    id: str | None = None
    description: str
    severity: str = "medium"
    mitigation: str | None = None
    agent: str | None = None


class ActionItem(BaseModel):
    id: str | None = None
    description: str
    owner: str | None = None
    due_date: str | None = None
    status: str = "pending"


class StakeholderItem(BaseModel):
    name: str
    role: str | None = None
    influence: str | None = None


class DashboardSnapshotBase(BaseModel):
    health: str = "green"
    risks: list[RiskItem] = []
    actions: list[ActionItem] = []
    timeline: dict = {}
    stakeholders: list[StakeholderItem] = []
    kpis: list[dict] = []
    next_steps: list[dict] = []
    generated_by_agents: list[str] = []


class DashboardSnapshot(DashboardSnapshotBase):
    id: UUID
    project_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}
