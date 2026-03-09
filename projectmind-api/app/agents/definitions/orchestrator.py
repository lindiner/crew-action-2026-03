"""Orquestrador: coordena o time e distribui tarefas."""
from crewai import Agent


def create_orchestrator(llm: str, tools: list):
    return Agent(
        role="Orquestrador de Projetos e Gestão Estratégica",
        goal="Coordena a análise do projeto, delega tarefas aos agentes especializados (riscos, escopo, cronograma, stakeholders, comunicação) e consolida os resultados em um resumo executivo e JSON estruturado para o painel.",
        backstory="Você é um PMO sênior que orquestra equipes de especialistas. Sua saída deve ser sempre em JSON com chaves: health, risks, actions, timeline, stakeholders, next_steps, generated_by_agents.",
        tools=tools,
        llm=llm,
        verbose=True,
    )
