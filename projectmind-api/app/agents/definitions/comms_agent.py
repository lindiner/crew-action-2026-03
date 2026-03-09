"""Agente de Comunicação: consolida outputs."""
from crewai import Agent


def create_comms_agent(llm: str, tools: list):
    return Agent(
        role="Comunicação do Projeto",
        goal="Consolida as análises dos outros agentes em um resumo executivo claro e em JSON padronizado para o painel: health, risks, actions, timeline, stakeholders, next_steps, generated_by_agents.",
        backstory="Comunicador técnico que transforma análises complexas em mensagens claras para a liderança.",
        tools=tools,
        llm=llm,
        verbose=True,
    )
