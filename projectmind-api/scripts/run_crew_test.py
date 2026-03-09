#!/usr/bin/env python3
"""
Testa os agentes CrewAI do ProjectMind localmente.

Requisitos: .env com OPENROUTER_API_KEY (ou copie de crewAI/verificacao) e litellm instalado.

Uso (na raiz do projectmind-api):
  python3 scripts/run_crew_test.py           # teste rápido: 1 agente (risk_agent)
  python3 scripts/run_crew_test.py --chat   # chat com orquestrador
  python3 scripts/run_crew_test.py --full   # crew completa (2-5 min)
"""
import asyncio
import argparse
import os
import sys

# Evita prompt interativo do CrewAI (traces)
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")

# Garante que o diretório raiz do projeto está no path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Carrega .env: primeiro projectmind-api, depois crewAI/verificacao (para testar com OpenRouter)
from pathlib import Path
root = Path(__file__).resolve().parents[1]
env_file = root / ".env"
verificacao_env = root.parent / "crewAI" / "verificacao" / ".env"
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)
    print(f"[OK] .env carregado de {env_file}")
elif verificacao_env.exists():
    from dotenv import load_dotenv
    load_dotenv(verificacao_env)
    print(f"[OK] .env carregado de {verificacao_env} (crewAI/verificacao)")
else:
    print(f"[AVISO] Nenhum .env em {root} nem em {verificacao_env}. Defina OPENROUTER_API_KEY ou ANTHROPIC_API_KEY.")

from app.agents.crew_manager import ProjectMindCrew


CONTEXTO_TESTE = """
Reunião de status do projeto Alpha - 05/03/2025

Participantes: Ana (PM), Bruno (Tech Lead), Carla (Stakeholder)

Resumo: O cronograma está atrasado em 2 semanas por causa da dependência com a API externa de pagamentos.
Bruno mencionou risco de não termos ambiente de homologação a tempo. Carla pediu relatório semanal.
Decisão: Contratar consultor para acelerar a integração de pagamentos até dia 20.
Ações: Ana vai enviar o relatório toda sexta. Bruno vai alinhar com infra sobre o ambiente.
"""


async def test_single_agent():
    """Teste rápido: apenas o agente de riscos com uma tarefa."""
    print("\n" + "=" * 60)
    print("TESTE 1: Agente de Riscos (single agent)")
    print("=" * 60)
    crew = ProjectMindCrew(
        project_id="test-project-001",
        active_agents=["risk_agent"],
        context=CONTEXTO_TESTE,
    )
    task_desc = f"Identifique os riscos no seguinte contexto de reunião:\n{CONTEXTO_TESTE[:1500]}"
    from crewai import Task, Crew
    agents = crew.build_agents()
    agent = agents["risk_agent"]
    task = Task(description=task_desc, expected_output="Lista de riscos em JSON ou texto claro.", agent=agent)
    c = Crew(agents=[agent], tasks=[task], verbose=True)
    print("\nExecutando... (pode levar 30-60s)\n")
    result = await asyncio.to_thread(c.kickoff)
    print("\n--- RESULTADO ---")
    print(result)
    return result


async def test_chat():
    """Teste de chat: pergunta ao orquestrador."""
    print("\n" + "=" * 60)
    print("TESTE 2: Chat com Orquestrador")
    print("=" * 60)
    crew = ProjectMindCrew(
        project_id="test-project-001",
        active_agents=["orchestrator", "comms_agent"],
        context=CONTEXTO_TESTE,
    )
    pergunta = "Quais são os 3 principais riscos deste projeto e o que fazer para cada um?"
    print(f"Pergunta: {pergunta}\n")
    print("Executando... (pode levar 30-60s)\n")
    resposta = await crew.chat(user_message=pergunta, target_agent="orchestrator")
    print("\n--- RESPOSTA ---")
    print(resposta)
    return resposta


async def test_full_crew():
    """Teste da crew completa: análise hierárquica."""
    print("\n" + "=" * 60)
    print("TESTE 3: Crew completa (análise para dashboard)")
    print("=" * 60)
    crew = ProjectMindCrew(
        project_id="test-project-001",
        active_agents=[
            "orchestrator",
            "risk_agent",
            "scope_agent",
            "schedule_agent",
            "stakeholder_agent",
            "comms_agent",
        ],
        context=CONTEXTO_TESTE,
    )
    print("Executando crew hierárquica... (pode levar 2-5 min)\n")
    result = await crew.run_analysis()
    print("\n--- RESULTADO (JSON para dashboard) ---")
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def main():
    parser = argparse.ArgumentParser(description="Testa agentes CrewAI do ProjectMind")
    parser.add_argument("--full", action="store_true", help="Roda a crew completa (mais lento)")
    parser.add_argument("--chat", action="store_true", help="Testa apenas o chat com orquestrador")
    parser.add_argument("--quick", action="store_true", help="Apenas 1 agente (default se nada for passado)")
    args = parser.parse_args()

    if args.full:
        asyncio.run(test_full_crew())
    elif args.chat:
        asyncio.run(test_chat())
    else:
        # default: teste rápido com 1 agente
        asyncio.run(test_single_agent())


if __name__ == "__main__":
    main()
