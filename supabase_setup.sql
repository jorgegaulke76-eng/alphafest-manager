-- ALPHAFEST MANAGER 3.0 - Execute todo este arquivo no SQL Editor do Supabase.

create table if not exists public.app_data (
    key text primary key,
    value jsonb not null default '[]'::jsonb,
    updated_at timestamptz not null default now()
);

alter table public.app_data enable row level security;

drop policy if exists "alphafest_select" on public.app_data;
drop policy if exists "alphafest_insert" on public.app_data;
drop policy if exists "alphafest_update" on public.app_data;
drop policy if exists "alphafest_delete" on public.app_data;

create policy "alphafest_select" on public.app_data for select to anon using (true);
create policy "alphafest_insert" on public.app_data for insert to anon with check (true);
create policy "alphafest_update" on public.app_data for update to anon using (true) with check (true);
create policy "alphafest_delete" on public.app_data for delete to anon using (true);

insert into storage.buckets (id, name, public)
values ('catalogo', 'catalogo', true)
on conflict (id) do update set public = true;

drop policy if exists "catalogo_public_read" on storage.objects;
drop policy if exists "catalogo_anon_insert" on storage.objects;
drop policy if exists "catalogo_anon_update" on storage.objects;
drop policy if exists "catalogo_anon_delete" on storage.objects;

create policy "catalogo_public_read" on storage.objects
for select to public using (bucket_id = 'catalogo');

create policy "catalogo_anon_insert" on storage.objects
for insert to anon with check (bucket_id = 'catalogo');

create policy "catalogo_anon_update" on storage.objects
for update to anon using (bucket_id = 'catalogo') with check (bucket_id = 'catalogo');

create policy "catalogo_anon_delete" on storage.objects
for delete to anon using (bucket_id = 'catalogo');
