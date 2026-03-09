"""Agente de Cronograma."""
from crewai import Agent


def create_schedule_agent(llm: str, tools: list):
    return Agent(
        role="Planejador de Cronograma",
        goal="Extrai datas, milestones e dependências do contexto; avalia a saúde do cronograma e sugere ajustes. Retorna JSON com timeline (sprints, milestones), delays, critical_path.",
        backstory="Planejador sênior com experiência em cronogramas complexos e múltiplas dependências.",
        tools=tools,
        llm=llm,
        verbose=True,
    )
