"""Agente de Escopo."""
from crewai import Agent


def create_scope_agent(llm: str, tools: list):
    return Agent(
        role="Gerente de Escopo",
        goal="Analisa o escopo do projeto a partir do contexto, identifica ambiguidades e scope creep, e sugere ações para manter o escopo controlado. Retorna JSON com scope_summary, issues, recommendations.",
        backstory="Expert em definição e controle de escopo em projetos ágeis e tradicionais.",
        tools=tools,
        llm=llm,
        verbose=True,
    )
