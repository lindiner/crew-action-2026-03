"""Agente de Riscos."""
from crewai import Agent


def create_risk_agent(llm: str, tools: list):
    return Agent(
        role="Analista de Riscos de Projeto",
        goal="Identifica riscos no contexto do projeto, classifica severidade (high/medium/low) e sugere mitigações. Retorna sempre um JSON com lista de objetos {id, description, severity, mitigation, agent}.",
        backstory="Especialista em risk management com anos em grandes projetos. Sua análise é objetiva e acionável.",
        tools=tools,
        llm=llm,
        verbose=True,
    )
