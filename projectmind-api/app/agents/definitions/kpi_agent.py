"""Agente de KPIs e Métricas."""
from crewai import Agent


def create_kpi_agent(llm, tools: list):
    return Agent(
        role="Analista de KPIs e Métricas de Projeto",
        goal="Extrai ou infere KPIs mensuráveis do contexto: progresso, prazo, qualidade, entregáveis, velocity. Retorna JSON com kpis[] (name, value, unit, trend, target, status).",
        backstory="Especialista em métricas de projeto e dashboards. Transforma contexto em indicadores acionáveis.",
        tools=tools,
        llm=llm,
        verbose=True,
    )
