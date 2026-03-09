"""Agente de Impedimentos/Blocos."""
from crewai import Agent


def create_blocker_agent(llm, tools: list):
    return Agent(
        role="Analista de Impedimentos e Blocos",
        goal="Identifica impedimentos ativos, dependências externas e gargalos que travam o time. Retorna JSON com blockers[] (description, owner, priority, suggested_action).",
        backstory="Expert em remoção de bloqueios e gestão de dependências em times ágeis. Foco no que está travando agora.",
        tools=tools,
        llm=llm,
        verbose=True,
    )
