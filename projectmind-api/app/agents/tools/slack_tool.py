"""
Tool wrapper para MCP Slack: enviar mensagem e listar canais.
"""
from typing import Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from app.config import settings


class SlackSendInput(BaseModel):
    """Input para enviar mensagem no Slack."""

    channel: str = Field(description="ID ou nome do canal")
    message: str = Field(description="Texto da mensagem")


class SlackTool(BaseTool):
    name: str = "slack_send"
    description: str = (
        "Envia mensagem para um canal do Slack. "
        "Use para comunicar decisões ou lembretes ao time. "
        "Requer integração Slack configurada."
    )
    args_schema: Type[BaseModel] = SlackSendInput

    def _run(self, channel: str, message: str) -> str:
        if not settings.slack_bot_token:
            return "Integração Slack não configurada. Configure SLACK_BOT_TOKEN."
        try:
            import httpx
            url = "https://slack.com/api/chat.postMessage"
            headers = {"Authorization": f"Bearer {settings.slack_bot_token}", "Content-Type": "application/json"}
            payload = {"channel": channel, "text": message}
            with httpx.Client(timeout=10.0) as client:
                r = client.post(url, headers=headers, json=payload)
            if r.status_code != 200:
                return f"Slack API error: {r.status_code}"
            data = r.json()
            if not data.get("ok"):
                return f"Slack error: {data.get('error', 'unknown')}"
            return "Mensagem enviada com sucesso."
        except Exception as e:
            return f"Erro ao enviar no Slack: {e}"
