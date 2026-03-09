"""
Modelos para execuções de agentes (CrewAI runs).
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class AgentRunBase(BaseModel):
    project_id: UUID
    ingestion_id: UUID | None = None
    agent_type: str
    input_context: str | None = None
    output: dict | None = None
    status: str = "pending"
    duration_ms: int | None = None


class AgentRunCreate(AgentRunBase):
    pass


class AgentRun(AgentRunBase):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentTeamConfig(BaseModel):
    agent_type: str
    active: bool = True
    config: dict | None = None


class AgentTeamUpdate(BaseModel):
    agents: list[AgentTeamConfig]


class SuggestTeamRequest(BaseModel):
    """Contexto opcional para análise (transcrição/email). Se enviado, a sugestão é síncrona."""
    context: str | None = None
