"""
Modelos Pydantic para Projetos e membros.
Alinhados com o schema do banco (003_schema_fixes.sql) e o PRD.
"""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field

ProjectStatus = Literal["active", "paused", "on_hold", "completed", "archived"]
OrchestratorMode = Literal["sequential", "hierarchical"]


class ProjectCreate(BaseModel):
    name: str
    objective: str = ""
    description: str | None = None          # alias legado; prioriza objective
    status: ProjectStatus = "active"
    orchestration_mode: OrchestratorMode = "hierarchical"
    metadata: dict = Field(default_factory=dict)


class ProjectUpdate(BaseModel):
    name: str | None = None
    objective: str | None = None
    description: str | None = None
    status: ProjectStatus | None = None
    orchestration_mode: OrchestratorMode | None = None
    context_summary: str | None = None
    health: str | None = None
    metadata: dict | None = None


class Project(BaseModel):
    id: UUID
    owner_id: UUID
    name: str
    objective: str | None = None
    description: str | None = None
    status: str = "active"
    health: str = "green"
    orchestration_mode: str = "hierarchical"
    context_summary: str | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectMember(BaseModel):
    project_id: UUID
    user_id: UUID
    role: str = "member"

    model_config = {"from_attributes": True}
