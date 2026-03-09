"""Agente de Stakeholders."""
from crewai import Agent


def create_stakeholder_agent(llm: str, tools: list):
    return Agent(
        role="Analista de Stakeholders",
        goal="Mapeia stakeholders mencionados no contexto, identifica papéis e influência, e sugere estratégias de comunicação. Retorna JSON com lista de {name, role, influence} e recommendations.",
        backstory="Especialista em gestão de stakeholders e comunicação executiva.",
        tools=tools,
        llm=llm,
        verbose=True,
    )
