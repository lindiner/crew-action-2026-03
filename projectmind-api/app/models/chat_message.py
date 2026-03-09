"""
Modelos para mensagens do chat com agentes.
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class ChatMessageBase(BaseModel):
    sender_type: str  # 'user' | 'agent'
    sender_id: str | None = None
    agent_type: str | None = None
    content: str
    structured_content: dict | None = None


class ChatMessageCreate(BaseModel):
    content: str
    target_agent: str | None = None


class ChatMessage(ChatMessageBase):
    id: UUID
    project_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}
