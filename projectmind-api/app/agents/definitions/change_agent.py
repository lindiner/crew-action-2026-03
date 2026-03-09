"""Agente de Mudança e Impacto."""
from crewai import Agent


def create_change_agent(llm, tools: list):
    return Agent(
        role="Analista de Mudança e Impacto",
        goal="Analisa pedidos de mudança e impacto em escopo, cronograma e custo. Retorna JSON com change_requests[], impact_analysis, recommendation (accept/reject/conditional).",
        backstory="Especialista em change control e análise de impacto. Avalia trade-offs de forma objetiva.",
        tools=tools,
        llm=llm,
        verbose=True,
    )
