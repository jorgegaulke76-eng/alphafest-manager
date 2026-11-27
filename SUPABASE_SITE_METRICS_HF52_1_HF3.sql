-- AlphaFest HF52.1-HF3 — habilita eventos de busca no painel privado.
-- Execute UMA vez no SQL Editor do Supabase antes de publicar o HF52.1-HF3.

alter table public.site_metrics_events
  drop constraint if exists site_metrics_events_event_type_check;

alter table public.site_metrics_events
  add constraint site_metrics_events_event_type_check
  check (event_type in ('page_view','product_open','whatsapp_click','search'));

drop policy if exists "public_insert_site_metrics"
  on public.site_metrics_events;

create policy "public_insert_site_metrics"
  on public.site_metrics_events
  for insert
  to anon, authenticated
  with check (
    event_type in ('page_view','product_open','whatsapp_click','search')
    and length(product_name) <= 180
    and length(page_path) <= 300
    and length(referrer) <= 500
    and length(client_id) <= 100
    and length(session_id) <= 100
  );
