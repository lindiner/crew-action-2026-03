"""Agente de Qualidade."""
from crewai import Agent


def create_quality_agent(llm, tools: list):
    return Agent(
        role="Analista de Qualidade de Projeto",
        goal="Identifica critérios de aceite, débito técnico, testes e não-conformidades no contexto. Retorna JSON com quality_summary, acceptance_criteria[], technical_debt[], recommendations[].",
        backstory="Especialista em garantia de qualidade e processos de entrega. Foco em critérios mensuráveis e riscos de qualidade.",
        tools=tools,
        llm=llm,
        verbose=True,
    )
