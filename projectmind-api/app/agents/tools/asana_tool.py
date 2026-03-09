"""
Tool wrapper para MCP Asana: listar tarefas e projetos.
"""
from typing import Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from app.config import settings


class AsanaSearchInput(BaseModel):
    """Input para busca no Asana."""

    project_gid: str = Field(default="", description="ID do projeto Asana (opcional)")
    query: str = Field(description="Termo de busca ou status (e.g. 'pendente')")


class AsanaTool(BaseTool):
    name: str = "asana_search"
    description: str = (
        "Consulta tarefas e projetos no Asana. "
        "Use quando precisar de status de tarefas, prazos ou lista de projetos. "
        "Requer integração Asana configurada."
    )
    args_schema: Type[BaseModel] = AsanaSearchInput

    def _run(self, project_gid: str = "", query: str = "") -> str:
        if not settings.asana_access_token:
            return "Integração Asana não configurada. Configure ASANA_ACCESS_TOKEN."
        try:
            import httpx
            headers = {"Authorization": f"Bearer {settings.asana_access_token}"}
            if project_gid:
                url = f"https://app.asana.com/api/1.0/projects/{project_gid}/tasks"
            else:
                url = "https://app.asana.com/api/1.0/workspaces"
            with httpx.Client(timeout=10.0) as client:
                r = client.get(url, headers=headers)
            if r.status_code != 200:
                return f"Asana API error: {r.status_code}"
            data = r.json()
            if "data" in data:
                return str(data["data"][:10])  # resumo
            return str(data)
        except Exception as e:
            return f"Erro ao consultar Asana: {e}"
