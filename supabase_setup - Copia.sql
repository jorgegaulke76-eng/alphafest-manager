-- ALPHAFEST MANAGER 20.4.9-I8.13.3 — SETUP SEGURO / CUSTO ZERO
-- Pré-requisito: configure SUPABASE_SERVICE_KEY nos Secrets do Streamlit.
-- O Manager é uma aplicação server-side; dados internos não precisam de escrita anônima.

create table if not exists public.app_data (
    key text primary key,
    value jsonb not null default '[]'::jsonb,
    updated_at timestamptz not null default now()
);

alter table public.app_data enable row level security;

-- Remove políticas legadas que permitiam acesso anônimo aos dados internos.
drop policy if exists "alphafest_select" on public.app_data;
drop policy if exists "alphafest_insert" on public.app_data;
drop policy if exists "alphafest_update" on public.app_data;
drop policy if exists "alphafest_delete" on public.app_data;
revoke all on table public.app_data from anon;

-- Bucket público SOMENTE para leitura do catálogo publicado.
insert into storage.buckets (id, name, public)
values ('catalogo', 'catalogo', true)
on conflict (id) do update set public = true;

drop policy if exists "catalogo_public_read" on storage.objects;
drop policy if exists "catalogo_anon_insert" on storage.objects;
drop policy if exists "catalogo_anon_update" on storage.objects;
drop policy if exists "catalogo_anon_delete" on storage.objects;

create policy "catalogo_public_read" on storage.objects
for select to public using (bucket_id = 'catalogo');

-- Escrita/leitura interna é realizada pelo servidor usando service_role, que
-- ignora RLS. Nunca exponha SUPABASE_SERVICE_KEY no GitHub ou navegador.
