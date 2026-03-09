"""
ProjectMind AI - FastAPI app entry point.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.supabase_client import init_supabase
from app.api.routes import auth, projects, ingestion, agents, dashboard, chat, integrations
from app.api.routes import custom_agents


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_supabase()
    yield
    # shutdown if needed


app = FastAPI(
    title=settings.app_name,
    description="API de gestão estratégica de projetos com multi-agentes CrewAI",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth
app.include_router(auth.router)

# Projects (inclui sub-rotas que usam prefix /projects)
app.include_router(projects.router)

# Ingestão: /projects/{id}/ingest
app.include_router(ingestion.router)

# Agentes: /projects/{id}/team, /agents/catalog
app.include_router(agents.router)

# Dashboard: /projects/{id}/dashboard
app.include_router(dashboard.router)

# Chat: /projects/{id}/chat
app.include_router(chat.router)

# Integrações
app.include_router(integrations.router)

# Agentes customizados: /agents/custom
app.include_router(custom_agents.router)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}
