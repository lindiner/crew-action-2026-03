# ProjectMind AI — Backend MVP

API de gestão estratégica de projetos com multi-agentes de IA orquestrados via CrewAI.

## Stack

- **Runtime:** Python 3.11+
- **API:** FastAPI + Pydantic v2
- **Banco:** Supabase (PostgreSQL + pgvector)
- **Auth:** Supabase Auth (JWT)
- **Agentes:** CrewAI
- **LLM:** Anthropic Claude (`claude-sonnet-4-20250514`)
- **Embeddings:** OpenAI `text-embedding-3-small` (1536 dims, pgvector)
- **Integrações:** Asana, Slack (MCP/HTTP)

## Setup

1. **Clone e venv**

```bash
cd projectmind-api
python3.11 -m venv .venv
source .venv/bin/activate  # ou .venv\Scripts\activate no Windows
pip install -r requirements.txt
```

2. **Variáveis de ambiente**

Copie `.env.example` para `.env` e preencha:

- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` — obrigatório
- `ANTHROPIC_API_KEY` — para CrewAI/Claude
- `OPENAI_API_KEY` — para embeddings (pgvector 1536)
- Opcional: `ASANA_ACCESS_TOKEN`, `SLACK_BOT_TOKEN`, `REDIS_URL`

3. **Supabase**

- Crie um projeto no [Supabase](https://supabase.com).
- No SQL Editor, execute na ordem:
  - `app/db/migrations/001_initial_schema.sql`
  - `app/db/migrations/002_match_project_memory_rpc.sql`
- Em Authentication > Providers, ative Email e defina um usuário de teste se quiser.
- **Modo sem login (frontend sem token):** para criar projetos, `projects.owner_id` precisa existir em `auth.users`. Crie um usuário em **Authentication → Users → Add user** (ex.: email `dev@localhost`, senha qualquer). Copie o **UUID** do usuário e no `.env` defina `DEV_USER_ID=<esse-uuid>`. Se a tabela `profiles` existir e tiver FK em `auth.users`, insira o perfil no SQL Editor: `insert into public.profiles (id, full_name) values ('<uuid-do-usuario>', 'Dev') on conflict (id) do nothing;`

4. **CrewAI — OpenRouter (padrão)**

Uma chave, vários modelos (Gemini, Claude, etc.) via [OpenRouter](https://openrouter.ai/):

```bash
CREWAI_API_KEY=sk-or-v1-...   # em https://openrouter.ai/keys
CREWAI_MODEL=openrouter/google/gemini-2.0-flash
```

Outros modelos: `openrouter/anthropic/claude-3-haiku`, `openrouter/google/gemini-2.5-flash`, etc.

### Testar os agentes CrewAI localmente

Na raiz do `projectmind-api`, com `.env` (ou o de `crewAI/verificacao`) carregado:

```bash
python3 scripts/run_crew_test.py           # 1 agente (risk_agent) ~30s
python3 scripts/run_crew_test.py --chat   # chat com orquestrador
python3 scripts/run_crew_test.py --full   # crew completa
```

(No macOS use `python3`; se tiver `python` no PATH pode usar `python`.)

5. **Rodar a API**

```bash
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --reload-dir app
```

O `--reload-dir app` evita recarregar ao alterar arquivos dentro de `.venv`.

Docs: http://localhost:8000/docs

## Exemplos de uso

### Criar projeto e listar

```bash
# Login (retorna token)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"seu@email.com","password":"sua-senha"}'

# Listar projetos (use o token no header)
curl -H "Authorization: Bearer SEU_TOKEN" http://localhost:8000/projects

# Criar projeto
curl -X POST http://localhost:8000/projects \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Meu Projeto","description":"Descrição do projeto"}'
```

### Chat com agentes CrewAI

```bash
# Enviar mensagem no chat do projeto
curl -X POST "http://localhost:8000/projects/{project_id}/chat" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"Quais são os principais riscos deste projeto?"}'

# Streaming (SSE)
curl -H "Authorization: Bearer SEU_TOKEN" \
  "http://localhost:8000/projects/{project_id}/chat/stream?q=Resuma o escopo"
```

### Testar agentes localmente (script)

```bash
python3 scripts/run_crew_test.py           # 1 agente
python3 scripts/run_crew_test.py --chat   # chat com orquestrador
python3 scripts/run_crew_test.py --full   # crew completa
```

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| **Auth** | | |
| POST | `/auth/login` | Login (email/senha) |
| POST | `/auth/logout` | Logout |
| GET | `/auth/me` | Perfil do usuário |
| **Projetos** | | |
| GET | `/projects` | Lista projetos |
| POST | `/projects` | Cria projeto |
| GET | `/projects/{id}` | Detalhes |
| PATCH | `/projects/{id}` | Atualiza |
| DELETE | `/projects/{id}` | Arquiva |
| **Ingestão** | | |
| POST | `/projects/{id}/ingest` | Nova ingestão (body: type, content) |
| GET | `/projects/{id}/ingest/{ingestion_id}` | Status da ingestão |
| **Agentes** | | |
| GET | `/agents/catalog` | Catálogo de agentes |
| GET | `/projects/{id}/team` | Time do projeto |
| POST | `/projects/{id}/team` | Atualiza time |
| **Dashboard** | | |
| GET | `/projects/{id}/dashboard` | Último snapshot |
| GET | `/projects/{id}/dashboard/history` | Histórico |
| POST | `/projects/{id}/dashboard/refresh` | Dispara nova análise |
| **Chat** | | |
| GET | `/projects/{id}/chat` | Histórico de mensagens |
| POST | `/projects/{id}/chat` | Envia mensagem (body: content, target_agent?) |
| GET | `/projects/{id}/chat/stream?q=...` | SSE streaming |
| **Integrações** | | |
| GET | `/integrations` | Status (Asana, Slack) |
| POST | `/integrations/asana/connect` | (MVP: 501) |
| POST | `/integrations/slack/connect` | (MVP: 501) |

## Estrutura

```
app/
├── main.py              # FastAPI app
├── config.py            # Settings (pydantic-settings)
├── api/routes/          # Auth, projects, ingestion, agents, dashboard, chat, integrations
├── api/deps.py          # get_current_user_id, profile
├── agents/
│   ├── crew_manager.py  # ProjectMindCrew (build_agents, build_tasks, run_analysis, chat)
│   ├── definitions/     # orchestrator, risk, scope, schedule, stakeholder, comms
│   └── tools/           # memory_tool, asana_tool, slack_tool
├── services/            # ingestion, embedding, dashboard, mcp
├── models/              # Pydantic (project, agent_run, dashboard, chat, ingestion)
└── db/                  # supabase_client, migrations
```

## Deploy

- **Supabase Edge Functions:** adaptar handlers para Deno se quiser rodar na borda.
- **Railway / Render:** use `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

## Licença

MIT.
