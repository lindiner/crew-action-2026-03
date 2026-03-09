"""
Modelos para ingestão de contexto (transcrições, e-mails, documentos).
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class IngestionCreate(BaseModel):
    type: str  # transcript | email | document
    content: str
    file_url: str | None = None


class Ingestion(BaseModel):
    id: UUID
    project_id: UUID
    type: str
    raw_content: str
    parsed_summary: str | None = None
    extracted_entities: dict = {}
    status: str = "pending"
    created_at: datetime

    model_config = {"from_attributes": True}


class ParsedContext(BaseModel):
    """Resultado do parsing por Claude (ingestion_service)."""
    summary: str
    risks: list[dict] = []
    actions: list[dict] = []
    stakeholders: list[dict] = []
    dates: list[str] = []
    decisions: list[str] = []
