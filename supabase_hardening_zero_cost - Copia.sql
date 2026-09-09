-- ALPHAFEST MANAGER 20.4.9-I8.13.3 — HARDENING CUSTO ZERO
-- IMPORTANTE: execute SOMENTE depois de cadastrar SUPABASE_SERVICE_KEY
-- nos Secrets do Streamlit e confirmar no Health Monitor: 
-- "escrita protegida por credencial de servidor".

-- Dados internos: nenhum acesso anônimo direto.
alter table public.app_data enable row level security;

drop policy if exists "alphafest_select" on public.app_data;
drop policy if exists "alphafest_insert" on public.app_data;
drop policy if exists "alphafest_update" on public.app_data;
drop policy if exists "alphafest_delete" on public.app_data;

revoke all on table public.app_data from anon;

-- O catálogo publicado continua público para leitura, mas escrita fica somente
-- pelo servidor do Manager usando a SERVICE KEY.
drop policy if exists "catalogo_anon_insert" on storage.objects;
drop policy if exists "catalogo_anon_update" on storage.objects;
drop policy if exists "catalogo_anon_delete" on storage.objects;

drop policy if exists "catalogo_public_read" on storage.objects;
create policy "catalogo_public_read" on storage.objects
for select to public using (bucket_id = 'catalogo');

-- A service_role do Supabase ignora RLS e continua apta a ler/gravar no servidor.
