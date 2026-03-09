"""Agente de Custos/Orçamento."""
from crewai import Agent


def create_budget_agent(llm, tools: list):
    return Agent(
        role="Analista de Custos e Orçamento de Projeto",
        goal="Identifica menções a custo, orçamento, burn rate e ROI no contexto; alerta sobre estouro ou desvios; sugere projeções e otimizações. Retorna JSON com budget_summary, cost_alerts[], projections, recommendations.",
        backstory="Especialista em controle de custos e orçamento em projetos. Focado em números e tendências para apoiar decisões.",
        tools=tools,
        llm=llm,
        verbose=True,
    )
