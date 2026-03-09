-- Função RPC para busca semântica na memória do projeto (pgvector)
create or replace function match_project_memory(
  query_embedding vector(1536),
  match_project_id uuid,
  match_count int default 5
)
returns table (id uuid, content text, metadata jsonb, similarity float)
language plpgsql
as $$
begin
  return query
  select
    project_memory.id,
    project_memory.content,
    project_memory.metadata,
    1 - (project_memory.embedding <=> query_embedding) as similarity
  from project_memory
  where project_memory.project_id = match_project_id
    and project_memory.embedding is not null
  order by project_memory.embedding <=> query_embedding
  limit match_count;
end;
$$;
