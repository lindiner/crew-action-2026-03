"""
Modelos Pydantic para Agentes Customizados.
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class CustomAgentCreate(BaseModel):
    name: str
    description: str = ""
    role: str = Field(..., description="Papel/título do agente no CrewAI")
    goal: str = Field(..., description="Objetivo principal do agente")
    backstory: str = Field(default="", description="Contexto e expertise do agente")
    domain: str = "custom"
    is_public: bool = False


class CustomAgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    role: str | None = None
    goal: str | None = None
    backstory: str | None = None
    domain: str | None = None
    is_public: bool | None = None


class CustomAgent(BaseModel):
    id: UUID
    created_by: UUID
    name: str
    description: str = ""
    role: str
    goal: str
    backstory: str = ""
    domain: str = "custom"
    is_public: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
