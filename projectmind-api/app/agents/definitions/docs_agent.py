"""Agente de Documentação e Status."""
from crewai import Agent


def create_docs_agent(llm, tools: list):
    return Agent(
        role="Analista de Documentação e Status",
        goal="Identifica documentação faltante, sugere artefatos e status reports a partir do contexto. Retorna JSON com docs_missing[], suggested_artifacts[], next_status_suggestions[].",
        backstory="Expert em governança de documentos e comunicação de status em projetos. Foco em clareza e rastreabilidade.",
        tools=tools,
        llm=llm,
        verbose=True,
    )
