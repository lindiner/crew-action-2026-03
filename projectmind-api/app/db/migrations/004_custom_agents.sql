-- Migration 004: Agentes Customizados
-- Permite que usuários criem agentes com habilidades próprias e os compartilhem

create table public.custom_agents (
  id            uuid primary key default gen_random_uuid(),
  created_by    uuid not null references auth.users(id) on delete cascade,
  name          text not null,
  description   text default '',
  role          text not null,
  goal          text not null,
  backstory     text default '',
  domain        text default 'custom',
  is_public     boolean default false,
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);

-- RLS
alter table public.custom_agents enable row level security;

-- Dono pode fazer tudo
create policy "custom_agents_owner_all"
  on public.custom_agents
  for all
  using (auth.uid() = created_by);

-- Qualquer autenticado pode ler agentes públicos
create policy "custom_agents_read_public"
  on public.custom_agents
  for select
  using (is_public = true);

-- Índices
create index idx_custom_agents_created_by on public.custom_agents(created_by);
create index idx_custom_agents_public on public.custom_agents(is_public) where is_public = true;

-- Trigger para updated_at
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger custom_agents_updated_at
  before update on public.custom_agents
  for each row execute procedure public.set_updated_at();
