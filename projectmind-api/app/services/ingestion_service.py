"""
Parser de transcrições e e-mails com Claude; geração de embeddings.
"""
import json
import re
from anthropic import Anthropic

from app.config import settings
from app.models.ingestion import ParsedContext
from app.services.embedding_service import EmbeddingService


class IngestionService:
    def __init__(self):
        self._client = Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None
        self._embedding = EmbeddingService()

    async def parse_transcript(self, content: str) -> ParsedContext:
        """Extrai resumo, riscos, ações, stakeholders, datas e decisões de uma transcrição."""
        if not self._client:
            return ParsedContext(
                summary=content[:1500],
                risks=[],
                actions=[],
                stakeholders=[],
                dates=[],
                decisions=[],
            )
        prompt = """Analise a transcrição de reunião abaixo e extraia em JSON (use exatamente as chaves):
- summary: resumo executivo (1 parágrafo)
- risks: lista de riscos identificados [{description, severity}]
- actions: lista de ações com responsável [{description, owner}]
- stakeholders: lista de pessoas mencionadas [{name, role}]
- dates: lista de datas e deadlines mencionadas
- decisions: lista de decisões tomadas

Transcrição:
"""
        prompt += content[:12000]
        try:
            msg = self._client.messages.create(
                model=settings.anthropic_model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            text = msg.content[0].text if msg.content else ""
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                data = json.loads(match.group())
                return ParsedContext(
                    summary=data.get("summary", ""),
                    risks=data.get("risks", []),
                    actions=data.get("actions", []),
                    stakeholders=data.get("stakeholders", []),
                    dates=data.get("dates", []),
                    decisions=data.get("decisions", []),
                )
        except Exception:
            pass
        return ParsedContext(summary=content[:1500], risks=[], actions=[], stakeholders=[], dates=[], decisions=[])

    async def parse_email_thread(self, content: str) -> ParsedContext:
        """Identifica remetentes, tópicos, pendências e decisões em thread de e-mail."""
        if not self._client:
            return ParsedContext(summary=content[:1500], risks=[], actions=[], stakeholders=[], dates=[], decisions=[])
        prompt = """Analise o thread de e-mail abaixo e extraia em JSON:
- summary: resumo do assunto e conclusões
- risks: riscos mencionados
- actions: ações e pendências com responsável
- stakeholders: remetentes e destinatários com papel
- dates: prazos e datas
- decisions: decisões tomadas

E-mails:
"""
        prompt += content[:12000]
        try:
            msg = self._client.messages.create(
                model=settings.anthropic_model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            text = msg.content[0].text if msg.content else ""
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                data = json.loads(match.group())
                return ParsedContext(
                    summary=data.get("summary", ""),
                    risks=data.get("risks", []),
                    actions=data.get("actions", []),
                    stakeholders=data.get("stakeholders", []),
                    dates=data.get("dates", []),
                    decisions=data.get("decisions", []),
                )
        except Exception:
            pass
        return ParsedContext(summary=content[:1500], risks=[], actions=[], stakeholders=[], dates=[], decisions=[])

    async def generate_embedding(self, text: str) -> list[float]:
        """Gera embedding e retorna lista de 1536 dims."""
        return await self._embedding.generate_embedding_async(text)
