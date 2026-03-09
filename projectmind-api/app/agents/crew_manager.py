"""
Orquestração CrewAI: monta crew, tarefas e executa análise.
LLM configurado em app.agents.llm_config (modelos alinhados à plataforma CrewAI).
"""
import asyncio
import json
import re
import time
from typing import Any

from crewai import Agent, Task, Crew, Process, LLM

from app.agents.llm_config import get_crew_llm
from app.agents.definitions.orchestrator import create_orchestrator
from app.agents.definitions.risk_agent import create_risk_agent
from app.agents.definitions.scope_agent import create_scope_agent
from app.agents.definitions.schedule_agent import create_schedule_agent
from app.agents.definitions.stakeholder_agent import create_stakeholder_agent
from app.agents.definitions.comms_agent import create_comms_agent
from app.agents.definitions.budget_agent import create_budget_agent
from app.agents.definitions.blocker_agent import create_blocker_agent
from app.agents.definitions.kpi_agent import create_kpi_agent
from app.agents.definitions.quality_agent import create_quality_agent
from app.agents.definitions.resource_agent import create_resource_agent
from app.agents.definitions.change_agent import create_change_agent
from app.agents.definitions.docs_agent import create_docs_agent
from app.agents.tools import MemorySearchTool, AsanaTool, SlackTool


def _save_agent_run(project_id: str, agent_type: str, input_ctx: str, output: Any, duration_ms: int, ingestion_id: str | None = None):
    """Persiste execução individual do agente em agent_runs (best-effort)."""
    try:
        from app.db.supabase_client import supabase_admin
        supabase_admin().table("agent_runs").insert({
            "project_id": project_id,
            "ingestion_id": ingestion_id,
            "agent_type": agent_type,
            "input_context": input_ctx[:4000],
            "output": {"result": str(output)[:8000]} if output else None,
            "status": "done",
            "duration_ms": duration_ms,
        }).execute()
    except Exception:
        pass  # Não bloquear o fluxo por falha de logging


class ProjectMindCrew:
    def __init__(
        self,
        project_id: str,
        active_agents: list[str],
        context: str,
        orchestration_mode: str = "hierarchical",
        ingestion_id: str | None = None,
    ):
        self.project_id = project_id
        self.active_agents = active_agents
        self.context = context
        self.orchestration_mode = orchestration_mode
        self.ingestion_id = ingestion_id
        self.llm = get_crew_llm()
        self._agents: dict[str, Agent] = {}
        self._tasks: list[Task] = []

    def _get_tools(self) -> list:
        """Tools compartilhadas: memória vinculada ao project_id para o agente não precisar passar UUID."""
        return [MemorySearchTool(project_id=self.project_id), AsanaTool(), SlackTool()]

    def _build_custom_agent(self, agent_type: str, tools: list) -> Agent:
        """Instancia um agente customizado a partir da definição no banco."""
        agent_id = agent_type.split(":", 1)[1]
        from app.db.supabase_client import supabase_admin
        r = supabase_admin().table("custom_agents").select("*").eq("id", agent_id).execute()
        if not r.data:
            raise ValueError(f"Agente customizado não encontrado: {agent_id}")
        ca = r.data[0]
        return Agent(
            role=ca["role"],
            goal=ca["goal"],
            backstory=ca.get("backstory") or f"Especialista em {ca.get('domain', 'análise de projetos')}.",
            tools=tools,
            llm=self.llm,
            verbose=True,
        )

    def build_agents(self) -> dict[str, Agent]:
        """Instancia apenas os agentes ativos (nativos + customizados)."""
        tools = self._get_tools()
        mapping = {
            "orchestrator": lambda: create_orchestrator(self.llm, tools),
            "risk_agent": lambda: create_risk_agent(self.llm, tools),
            "scope_agent": lambda: create_scope_agent(self.llm, tools),
            "schedule_agent": lambda: create_schedule_agent(self.llm, tools),
            "stakeholder_agent": lambda: create_stakeholder_agent(self.llm, tools),
            "comms_agent": lambda: create_comms_agent(self.llm, tools),
            "budget_agent": lambda: create_budget_agent(self.llm, tools),
            "blocker_agent": lambda: create_blocker_agent(self.llm, tools),
            "kpi_agent": lambda: create_kpi_agent(self.llm, tools),
            "quality_agent": lambda: create_quality_agent(self.llm, tools),
            "resource_agent": lambda: create_resource_agent(self.llm, tools),
            "change_agent": lambda: create_change_agent(self.llm, tools),
            "docs_agent": lambda: create_docs_agent(self.llm, tools),
        }
        for name in self.active_agents:
            if name not in self._agents:
                if name in mapping:
                    self._agents[name] = mapping[name]()
                elif name.startswith("custom:"):
                    try:
                        self._agents[name] = self._build_custom_agent(name, tools)
                    except Exception as e:
                        # Agente customizado inválido — ignora e segue
                        import logging
                        logging.warning(f"Agente customizado ignorado ({name}): {e}")
        if "orchestrator" not in self._agents:
            self._agents["orchestrator"] = create_orchestrator(self.llm, tools)
        return self._agents

    def build_tasks(self, agents: dict[str, Agent]) -> list[Task]:
        """
        Tarefas para análise completa do dashboard.
        Modo sequencial: cada agente enriquece o contexto do anterior.
        Modo hierárquico: orquestrador delega e consolida (padrão CrewAI).
        """
        self._tasks = []
        ctx = self.context[:8000]
        ctx_short = ctx[:4000]

        if self.orchestration_mode == "sequential":
            # Pipeline linear — cada task alimenta a próxima via context
            if "orchestrator" in agents:
                self._tasks.append(Task(
                    description=f"Leia o contexto e produza um sumário executivo do projeto com os principais pontos de atenção.\nContexto:\n{ctx}",
                    expected_output="Sumário executivo em texto estruturado com health status (green/amber/red) e justificativa.",
                    agent=agents["orchestrator"],
                ))
            if "risk_agent" in agents:
                self._tasks.append(Task(
                    description=f"Com base no contexto e no sumário anterior, liste todos os riscos identificados.\nContexto:\n{ctx_short}",
                    expected_output='JSON: {{"risks": [{{"title":"","description":"","severity":"high|medium|low|critical","mitigation":"","owner":""}}]}}',
                    agent=agents["risk_agent"],
                    context=self._tasks[:1] if self._tasks else [],
                ))
            if "scope_agent" in agents:
                self._tasks.append(Task(
                    description=f"Analise o escopo no contexto: identifique scope creep, mudanças e recomendações.\nContexto:\n{ctx_short}",
                    expected_output='JSON: {{"scope_summary":"","issues":[],"recommendations":[]}}',
                    agent=agents["scope_agent"],
                    context=self._tasks[:1] if self._tasks else [],
                ))
            if "schedule_agent" in agents:
                self._tasks.append(Task(
                    description=f"Extraia o cronograma, milestones, datas e possíveis atrasos do contexto.\nContexto:\n{ctx_short}",
                    expected_output='JSON: {{"milestones":[{{"milestone":"","date":"","status":""}}],"delays":[],"critical_path":""}}',
                    agent=agents["schedule_agent"],
                    context=self._tasks[:1] if self._tasks else [],
                ))
            if "stakeholder_agent" in agents:
                self._tasks.append(Task(
                    description=f"Mapeie os stakeholders mencionados no contexto com influência e sentimento.\nContexto:\n{ctx_short}",
                    expected_output='JSON: {{"stakeholders":[{{"name":"","role":"","influence":"high|medium|low","sentiment":"positive|neutral|negative"}}]}}',
                    agent=agents["stakeholder_agent"],
                    context=self._tasks[:1] if self._tasks else [],
                ))
            if "budget_agent" in agents:
                self._tasks.append(Task(
                    description=f"Analise custos, orçamento e burn rate no contexto; identifique alertas e projeções.\nContexto:\n{ctx_short}",
                    expected_output='JSON: {{"budget_summary":"","cost_alerts":[],"projections":"","recommendations":[]}}',
                    agent=agents["budget_agent"],
                    context=self._tasks[:1] if self._tasks else [],
                ))
            if "blocker_agent" in agents:
                self._tasks.append(Task(
                    description=f"Identifique impedimentos ativos, dependências externas e gargalos que travam o time.\nContexto:\n{ctx_short}",
                    expected_output='JSON: {{"blockers":[{{"description":"","owner":"","priority":"high|medium|low","suggested_action":""}}]}}',
                    agent=agents["blocker_agent"],
                    context=self._tasks[:1] if self._tasks else [],
                ))
            if "kpi_agent" in agents:
                self._tasks.append(Task(
                    description=f"Extraia KPIs e métricas do contexto: progresso, prazo, qualidade, entregáveis.\nContexto:\n{ctx_short}",
                    expected_output='JSON: {{"kpis":[{{"name":"","value":"","unit":"","trend":"up|down|stable","target":"","status":"on_track|at_risk|off_track"}}]}}',
                    agent=agents["kpi_agent"],
                    context=self._tasks[:1] if self._tasks else [],
                ))
            if "quality_agent" in agents:
                self._tasks.append(Task(
                    description=f"Identifique critérios de aceite, débito técnico e riscos de qualidade no contexto.\nContexto:\n{ctx_short}",
                    expected_output='JSON: {{"quality_summary":"","acceptance_criteria":[],"technical_debt":[],"recommendations":[]}}',
                    agent=agents["quality_agent"],
                    context=self._tasks[:1] if self._tasks else [],
                ))
            if "resource_agent" in agents:
                self._tasks.append(Task(
                    description=f"Analise alocação, capacidade da equipe e sobrecarga no contexto.\nContexto:\n{ctx_short}",
                    expected_output='JSON: {{"allocation_summary":"","capacity_issues":[],"recommendations":[]}}',
                    agent=agents["resource_agent"],
                    context=self._tasks[:1] if self._tasks else [],
                ))
            if "change_agent" in agents:
                self._tasks.append(Task(
                    description=f"Identifique pedidos de mudança e analise impacto em escopo, prazo e custo.\nContexto:\n{ctx_short}",
                    expected_output='JSON: {{"change_requests":[],"impact_analysis":"","recommendation":"accept|reject|conditional"}}',
                    agent=agents["change_agent"],
                    context=self._tasks[:1] if self._tasks else [],
                ))
            if "docs_agent" in agents:
                self._tasks.append(Task(
                    description=f"Identifique documentação faltante e sugira artefatos e status reports.\nContexto:\n{ctx_short}",
                    expected_output='JSON: {{"docs_missing":[],"suggested_artifacts":[],"next_status_suggestions":[]}}',
                    agent=agents["docs_agent"],
                    context=self._tasks[:1] if self._tasks else [],
                ))
            if "comms_agent" in agents:
                all_prev = self._tasks[:]
                self._tasks.append(Task(
                    description="Consolide TODAS as análises anteriores em um único JSON para o painel de gestão.",
                    expected_output='JSON: {{"health":"green|amber|red","risks":[],"actions":[],"timeline":{{}},"stakeholders":[],"kpis":[],"budget_alerts":[],"blockers":[],"next_steps":[],"generated_by_agents":[]}}',
                    agent=agents["comms_agent"],
                    context=all_prev,
                ))
        else:
            # Modo hierárquico — orquestrador recebe todos os resultados
            if "risk_agent" in agents:
                self._tasks.append(Task(
                    description=f"Identifique e analise todos os riscos do projeto.\nContexto:\n{ctx_short}",
                    expected_output='JSON: {{"risks":[{{"title":"","description":"","severity":"high|medium|low|critical","mitigation":"","owner":""}}]}}',
                    agent=agents["risk_agent"],
                ))
            if "scope_agent" in agents:
                self._tasks.append(Task(
                    description=f"Analise o escopo, identifique scope creep e recomendações.\nContexto:\n{ctx_short}",
                    expected_output='JSON: {{"scope_summary":"","issues":[],"recommendations":[]}}',
                    agent=agents["scope_agent"],
                ))
            if "schedule_agent" in agents:
                self._tasks.append(Task(
                    description=f"Mapeie milestones, datas, atrasos e caminho crítico.\nContexto:\n{ctx_short}",
                    expected_output='JSON: {{"milestones":[{{"milestone":"","date":"","status":""}}],"delays":[],"critical_path":""}}',
                    agent=agents["schedule_agent"],
                ))
            if "stakeholder_agent" in agents:
                self._tasks.append(Task(
                    description=f"Mapeie stakeholders com nome, papel, nível de influência e sentimento.\nContexto:\n{ctx_short}",
                    expected_output='JSON: {{"stakeholders":[{{"name":"","role":"","influence":"high|medium|low","sentiment":"positive|neutral|negative"}}]}}',
                    agent=agents["stakeholder_agent"],
                ))
            if "budget_agent" in agents:
                self._tasks.append(Task(
                    description=f"Analise custos, orçamento e burn rate; identifique alertas e projeções.\nContexto:\n{ctx_short}",
                    expected_output='JSON: {{"budget_summary":"","cost_alerts":[],"projections":"","recommendations":[]}}',
                    agent=agents["budget_agent"],
                ))
            if "blocker_agent" in agents:
                self._tasks.append(Task(
                    description=f"Identifique impedimentos ativos, dependências externas e gargalos.\nContexto:\n{ctx_short}",
                    expected_output='JSON: {{"blockers":[{{"description":"","owner":"","priority":"high|medium|low","suggested_action":""}}]}}',
                    agent=agents["blocker_agent"],
                ))
            if "kpi_agent" in agents:
                self._tasks.append(Task(
                    description=f"Extraia KPIs mensuráveis do contexto: progresso, prazo, qualidade, entregáveis.\nContexto:\n{ctx_short}",
                    expected_output='JSON: {{"kpis":[{{"name":"","value":"","unit":"","trend":"up|down|stable","target":"","status":"on_track|at_risk|off_track"}}]}}',
                    agent=agents["kpi_agent"],
                ))
            elif "orchestrator" in agents:
                self._tasks.append(Task(
                    description=f"Extraia KPIs mensuráveis do contexto: métricas de prazo, orçamento, qualidade, entregáveis.\nContexto:\n{ctx_short}",
                    expected_output='JSON: {{"kpis":[{{"name":"","value":"","unit":"","trend":"up|down|stable","target":"","status":"on_track|at_risk|off_track"}}]}}',
                    agent=agents["orchestrator"],
                ))
            if "quality_agent" in agents:
                self._tasks.append(Task(
                    description=f"Identifique critérios de aceite, débito técnico e riscos de qualidade.\nContexto:\n{ctx_short}",
                    expected_output='JSON: {{"quality_summary":"","acceptance_criteria":[],"technical_debt":[],"recommendations":[]}}',
                    agent=agents["quality_agent"],
                ))
            if "resource_agent" in agents:
                self._tasks.append(Task(
                    description=f"Analise alocação, capacidade da equipe e sobrecarga.\nContexto:\n{ctx_short}",
                    expected_output='JSON: {{"allocation_summary":"","capacity_issues":[],"recommendations":[]}}',
                    agent=agents["resource_agent"],
                ))
            if "change_agent" in agents:
                self._tasks.append(Task(
                    description=f"Identifique pedidos de mudança e analise impacto em escopo, prazo e custo.\nContexto:\n{ctx_short}",
                    expected_output='JSON: {{"change_requests":[],"impact_analysis":"","recommendation":"accept|reject|conditional"}}',
                    agent=agents["change_agent"],
                ))
            if "docs_agent" in agents:
                self._tasks.append(Task(
                    description=f"Identifique documentação faltante e sugira artefatos e status reports.\nContexto:\n{ctx_short}",
                    expected_output='JSON: {{"docs_missing":[],"suggested_artifacts":[],"next_status_suggestions":[]}}',
                    agent=agents["docs_agent"],
                ))
            if "comms_agent" in agents:
                all_prev = self._tasks[:]
                self._tasks.append(Task(
                    description="Consolide TODAS as análises anteriores em um único JSON para o painel de gestão estratégica.",
                    expected_output='JSON: {{"health":"green|amber|red","risks":[],"actions":[],"timeline":{{}},"stakeholders":[],"kpis":[],"budget_alerts":[],"blockers":[],"next_steps":[],"generated_by_agents":[]}}',
                    agent=agents["comms_agent"],
                    context=all_prev,
                ))
            elif "orchestrator" in agents:
                # Fallback: orquestrador consolida tudo
                all_prev = [t for t in self._tasks if t.agent != agents.get("orchestrator")]
                self._tasks.append(Task(
                    description=f"Consolide todas as análises em JSON para o painel.\nContexto:\n{ctx}",
                    expected_output='JSON: {{"health":"green|amber|red","risks":[],"actions":[],"timeline":{{}},"stakeholders":[],"kpis":[],"next_steps":[],"generated_by_agents":[]}}',
                    agent=agents["orchestrator"],
                    context=all_prev if all_prev else [],
                ))

        # Tarefas para agentes customizados (análise livre no domínio deles)
        custom_names = [n for n in self.active_agents if n.startswith("custom:") and n in agents]
        for cname in custom_names:
            cagent = agents[cname]
            self._tasks.append(Task(
                description=(
                    f"Como {cagent.role}, analise o contexto do projeto e produza insights "
                    f"relevantes ao seu domínio de especialidade.\nContexto:\n{ctx_short}"
                ),
                expected_output=(
                    "Análise estruturada em texto ou JSON com insights, recomendações e "
                    "pontos de atenção específicos do seu domínio."
                ),
                agent=cagent,
            ))

        if not self._tasks:
            fallback_agent = list(agents.values())[0]
            self._tasks = [Task(
                description=f"Analise o contexto e produza o JSON completo para o painel.\nContexto:\n{ctx}",
                expected_output='JSON: {{"health":"green|amber|red","risks":[],"actions":[],"timeline":{{}},"stakeholders":[],"kpis":[],"next_steps":[],"generated_by_agents":[]}}',
                agent=fallback_agent,
            )]
        return self._tasks

    def _parse_result(self, result: Any) -> dict | None:
        """Extrai JSON do output do crew."""
        raw = str(result) if result else ""
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {
            "health": "green",
            "risks": [],
            "actions": [],
            "timeline": {},
            "stakeholders": [],
            "kpis": [],
            "next_steps": [],
            "generated_by_agents": self.active_agents,
        }

    def _run_crew_sync(self) -> Any:
        """Execução síncrona do crew (para rodar em thread)."""
        agents = self.build_agents()
        tasks = self.build_tasks(agents)

        process = Process.sequential if self.orchestration_mode == "sequential" else Process.hierarchical

        crew_kwargs: dict[str, Any] = {
            "agents": list(agents.values()),
            "tasks": tasks,
            "process": process,
            "verbose": True,
        }
        if process == Process.hierarchical:
            manager = agents.get("orchestrator") or list(agents.values())[0]
            crew_kwargs["manager_agent"] = manager
            crew_kwargs["manager_llm"] = self.llm

        crew = Crew(**crew_kwargs)
        t0 = time.monotonic()
        result = crew.kickoff()
        duration = int((time.monotonic() - t0) * 1000)

        # Registrar execução no agent_runs (agente consolidador)
        _save_agent_run(
            project_id=self.project_id,
            agent_type="crew_analysis",
            input_ctx=self.context[:4000],
            output=result,
            duration_ms=duration,
            ingestion_id=self.ingestion_id,
        )
        return result

    async def run_analysis(self) -> dict:
        """Executa crew e retorna resultado estruturado para o dashboard."""
        result = await asyncio.to_thread(self._run_crew_sync)
        return self._parse_result(result) or {}

    async def chat(self, user_message: str, target_agent: str = "orchestrator") -> str:
        """Resposta do agente para mensagem do usuário (chat)."""
        agents = self.build_agents()
        agent = agents.get(target_agent) or agents.get("orchestrator") or list(agents.values())[0]
        task = Task(
            description=f"O usuário perguntou: {user_message}\n\nContexto do projeto (se relevante): {self.context[:3000]}",
            expected_output="Resposta clara e objetiva em texto, em português.",
            agent=agent,
        )
        crew = Crew(agents=[agent], tasks=[task], verbose=True)
        t0 = time.monotonic()
        result = await asyncio.to_thread(crew.kickoff)
        duration = int((time.monotonic() - t0) * 1000)
        _save_agent_run(
            project_id=self.project_id,
            agent_type=target_agent,
            input_ctx=user_message,
            output=result,
            duration_ms=duration,
        )
        return str(result) if result else "Sem resposta."

    async def suggest_team(self) -> dict:
        """
        Orquestrador analisa o contexto e sugere o time ideal de agentes com justificativas.
        Retorna: {agents: [{agent_type, active, justification}]}
        """
        agents = self.build_agents()
        orchestrator = agents.get("orchestrator") or list(agents.values())[0]
        available = [
            "risk_agent", "scope_agent", "schedule_agent", "stakeholder_agent",
            "comms_agent", "budget_agent", "blocker_agent", "kpi_agent",
            "quality_agent", "resource_agent", "change_agent", "docs_agent",
        ]
        task = Task(
            description=(
                f"Analise o contexto do projeto abaixo e sugira quais agentes são necessários para esta análise.\n"
                f"Agentes disponíveis: {available}\n"
                f"Para cada agente, indique se deve ser ativado (true/false) e justifique em 1 frase.\n\n"
                f"Contexto:\n{self.context[:6000]}"
            ),
            expected_output=(
                'JSON: {{"suggested_agents": ['
                '{{"agent_type": "risk_agent", "active": true, "justification": "..."}},'
                '...'
                ']}}'
            ),
            agent=orchestrator,
        )
        crew = Crew(agents=[orchestrator], tasks=[task], verbose=True)
        result = await asyncio.to_thread(crew.kickoff)
        raw = str(result) if result else ""
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            try:
                data = json.loads(match.group())
                suggested = data.get("suggested_agents", [])
                # Garantir orquestrador sempre ativo
                agent_types_in = {a["agent_type"] for a in suggested}
                if "orchestrator" not in agent_types_in:
                    suggested.insert(0, {"agent_type": "orchestrator", "active": True, "justification": "Sempre necessário para coordenar o time."})
                return {"suggested_agents": suggested}
            except json.JSONDecodeError:
                pass
        # Fallback: todos ativos
        return {
            "suggested_agents": [
                {"agent_type": "orchestrator", "active": True, "justification": "Coordena o time."},
                {"agent_type": "risk_agent", "active": True, "justification": "Análise de riscos recomendada."},
                {"agent_type": "scope_agent", "active": True, "justification": "Controle de escopo recomendado."},
                {"agent_type": "schedule_agent", "active": True, "justification": "Análise de cronograma recomendada."},
                {"agent_type": "stakeholder_agent", "active": True, "justification": "Mapeamento de stakeholders recomendado."},
                {"agent_type": "comms_agent", "active": True, "justification": "Consolidação e comunicação essenciais."},
                {"agent_type": "budget_agent", "active": True, "justification": "Análise de custos e orçamento."},
                {"agent_type": "blocker_agent", "active": True, "justification": "Identificação de impedimentos ativos."},
                {"agent_type": "kpi_agent", "active": True, "justification": "KPIs e métricas do projeto."},
                {"agent_type": "quality_agent", "active": True, "justification": "Análise de qualidade e critérios de aceite."},
                {"agent_type": "resource_agent", "active": True, "justification": "Gestão de recursos e capacidade."},
                {"agent_type": "change_agent", "active": True, "justification": "Análise de mudanças e impacto."},
                {"agent_type": "docs_agent", "active": True, "justification": "Documentação e status reports."},
            ]
        }
