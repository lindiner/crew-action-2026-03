"""Agente de Recursos e Capacidade."""
from crewai import Agent


def create_resource_agent(llm, tools: list):
    return Agent(
        role="Analista de Recursos e Capacidade",
        goal="Analisa alocação de pessoas, capacidade da equipe, sobrecarga e skills necessários vs disponíveis. Retorna JSON com allocation_summary, capacity_issues[], recommendations[].",
        backstory="Expert em planejamento de recursos e gestão de capacidade em projetos. Identifica gargalos e desbalanceamento.",
        tools=tools,
        llm=llm,
        verbose=True,
    )
