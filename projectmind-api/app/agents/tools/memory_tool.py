"""
Tool de busca em memória vetorial (RAG) no Supabase pgvector.
Quando project_id é passado no construtor, a tool já está vinculada ao projeto (o agente não precisa informar UUID).
"""
from typing import Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from app.db.supabase_client import supabase_admin


class MemorySearchInput(BaseModel):
    """Input para busca em memória (quando project_id não está vinculado)."""

    project_id: str = Field(description="UUID do projeto")
    query: str = Field(description="Pergunta ou termo para busca semântica")
    limit: int = Field(default=5, description="Máximo de resultados")


class MemorySearchInputBound(BaseModel):
    """Input quando o projeto já está vinculado à tool."""

    query: str = Field(description="Pergunta ou termo para busca semântica na memória do projeto")
    limit: int = Field(default=5, description="Máximo de resultados")


class MemorySearchTool(BaseTool):
    name: str = "memory_search"
    description: str = (
        "Busca no repositório de memória do projeto (RAG). "
        "Use para recuperar contexto relevante de ingestões e análises anteriores."
    )
    args_schema: Type[BaseModel] = MemorySearchInput

    def __init__(self, project_id: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self._project_id = project_id
        if project_id:
            self.description = (
                "Busca no repositório de memória deste projeto (RAG). "
                "Use para recuperar contexto relevante de ingestões e análises anteriores. "
                "Informe apenas a query (o projeto já está definido)."
            )
            self.args_schema = MemorySearchInputBound

    def _run(self, query: str, limit: int = 5, project_id: str | None = None) -> str:
        pid = self._project_id or project_id
        if not pid or pid == "default":
            return "Erro: project_id inválido. A busca na memória exige um UUID de projeto."
        if not query.strip():
            return "Query vazia."
        client = supabase_admin()
        if client is None:
            return "Memória do projeto indisponível (Supabase não configurado)."
        # Tenta busca vetorial se existir RPC e embedding
        try:
            from app.services.embedding_service import EmbeddingService
            emb_svc = EmbeddingService()
            query_embedding = emb_svc.generate_embedding_sync(query)
            if query_embedding:
                r = (
                    client
                    .rpc(
                        "match_project_memory",
                        {
                            "query_embedding": query_embedding,
                            "match_project_id": pid,
                            "match_count": limit,
                        },
                    )
                    .execute()
                )
                if r.data:
                    return "\n---\n".join([d.get("content", "") for d in r.data])
        except Exception:
            pass
        # Fallback: busca por project_id (últimos itens)
        r = (
            client
            .table("project_memory")
            .select("content, metadata")
            .eq("project_id", pid)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        if not r.data:
            return "Nenhum resultado na memória do projeto."
        return "\n---\n".join([d.get("content", "") for d in r.data])
