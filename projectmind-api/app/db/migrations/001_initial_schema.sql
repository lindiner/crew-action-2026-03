-- ProjectMind AI - Schema inicial (já descrito no README; execute no Supabase SQL Editor)
-- Este arquivo replica o schema para referência e migração manual.

create extension if not exists vector;

create table if not exists public.profiles (
  id uuid references auth.users primary key,
  full_name text,
  role text check (role in ('pm', 'pmo', 'tech_lead', 'executive')),
  avatar_url text,
  created_at timestamptz default now()
);

create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid references public.profiles(id) not null,
  name text not null,
  description text,
  status text default 'active' check (status in ('active', 'paused', 'completed', 'archived')),
  health text default 'green' check (health in ('green', 'yellow', 'red')),
  context_summary text,
  metadata jsonb default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.project_members (
  project_id uuid references public.projects(id) on delete cascade,
  user_id uuid references public.profiles(id),
  role text default 'member',
  primary key (project_id, user_id)
);

create table if not exists public.ingestions (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.projects(id) on delete cascade,
  type text check (type in ('transcript', 'email', 'document')),
  raw_content text not null,
  parsed_summary text,
  extracted_entities jsonb default '{}',
  embedding vector(1536),
  status text default 'pending' check (status in ('pending', 'processing', 'done', 'error')),
  created_at timestamptz default now()
);

create table if not exists public.agent_teams (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.projects(id) on delete cascade,
  agents jsonb not null,
  suggested_by_ai boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.agent_runs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.projects(id) on delete cascade,
  ingestion_id uuid references public.ingestions(id),
  agent_type text not null,
  input_context text,
  output jsonb,
  status text default 'pending' check (status in ('pending', 'running', 'done', 'error')),
  duration_ms integer,
  created_at timestamptz default now()
);

create table if not exists public.dashboard_snapshots (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.projects(id) on delete cascade,
  health text default 'green',
  risks jsonb default '[]',
  actions jsonb default '[]',
  timeline jsonb default '{}',
  stakeholders jsonb default '[]',
  kpis jsonb default '[]',
  next_steps jsonb default '[]',
  generated_by_agents text[],
  created_at timestamptz default now()
);

create table if not exists public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.projects(id) on delete cascade,
  sender_type text check (sender_type in ('user', 'agent')),
  sender_id text,
  agent_type text,
  content text not null,
  structured_content jsonb,
  created_at timestamptz default now()
);

create table if not exists public.project_memory (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.projects(id) on delete cascade,
  content text not null,
  embedding vector(1536),
  metadata jsonb default '{}',
  created_at timestamptz default now()
);

alter table public.projects enable row level security;
alter table public.ingestions enable row level security;
alter table public.chat_messages enable row level security;
alter table public.dashboard_snapshots enable row level security;

create policy "Users can access their projects"
  on public.projects for all
  using (owner_id = auth.uid() or id in (
    select project_id from public.project_members where user_id = auth.uid()
  ));

create policy "Users can access project ingestions"
  on public.ingestions for all
  using (project_id in (
    select id from public.projects where owner_id = auth.uid()
    union
    select project_id from public.project_members where user_id = auth.uid()
  ));

create policy "Users can access project chat"
  on public.chat_messages for all
  using (project_id in (
    select id from public.projects where owner_id = auth.uid()
    union
    select project_id from public.project_members where user_id = auth.uid()
  ));

create policy "Users can access project dashboards"
  on public.dashboard_snapshots for all
  using (project_id in (
    select id from public.projects where owner_id = auth.uid()
    union
    select project_id from public.project_members where user_id = auth.uid()
  ));

create index if not exists idx_project_memory_embedding on public.project_memory using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create index if not exists idx_ingestions_embedding on public.ingestions using ivfflat (embedding vector_cosine_ops) with (lists = 100);
