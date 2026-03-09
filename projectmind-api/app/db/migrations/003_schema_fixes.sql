-- Migration 003: Schema fixes alinhados com o PRD e modelos Python
-- Execute no Supabase SQL Editor

-- 1. Adicionar coluna `objective` em projects (campo principal do PRD)
alter table public.projects
  add column if not exists objective text;

-- 2. Adicionar coluna `orchestration_mode`
alter table public.projects
  add column if not exists orchestration_mode text default 'hierarchical'
    check (orchestration_mode in ('sequential', 'hierarchical'));

-- 3. Corrigir constraint de status para incluir 'on_hold'
--    (o constraint nomeado precisa ser dropado antes de recriar)
alter table public.projects
  drop constraint if exists projects_status_check;

alter table public.projects
  add constraint projects_status_check
    check (status in ('active', 'paused', 'on_hold', 'completed', 'archived'));

-- 4. Garantir que `kpis` existe em dashboard_snapshots (já estava no schema inicial)
alter table public.dashboard_snapshots
  add column if not exists kpis jsonb default '[]';

-- 5. Tabela agent_runs: garantir coluna orchestration_mode
--    (já existe no schema inicial, apenas confirmar)

-- 6. Índice para busca de projetos por owner
create index if not exists idx_projects_owner_id on public.projects(owner_id);
create index if not exists idx_projects_status on public.projects(status);

-- 7. Comentários para clareza
comment on column public.projects.objective is 'Objetivo estratégico do projeto (PRD: campo principal)';
comment on column public.projects.orchestration_mode is 'Modo de orquestração CrewAI: sequential ou hierarchical';
