-- AlphaFest HF65.12 — Inteligência de Acesso do Site
-- A migração oficial desta release adiciona somente metadados agregáveis e não coleta endereço exato.

alter table public.site_metrics_events
  add column if not exists city text not null default '',
  add column if not exists region text not null default '',
  add column if not exists country text not null default '',
  add column if not exists device_type text not null default '',
  add column if not exists browser text not null default '',
  add column if not exists traffic_source text not null default '',
  add column if not exists utm_source text not null default '',
  add column if not exists utm_medium text not null default '',
  add column if not exists utm_campaign text not null default '',
  add column if not exists entry_path text not null default '',
  add column if not exists event_context text not null default '';

alter table public.site_metrics_events drop constraint if exists site_metrics_events_event_type_check;
alter table public.site_metrics_events add constraint site_metrics_events_event_type_check
check (event_type in ('page_view','product_open','whatsapp_click','search','gallery_open','occasion_filter','category_filter'));

drop policy if exists "public_insert_site_metrics" on public.site_metrics_events;
create policy "public_insert_site_metrics" on public.site_metrics_events for insert to anon, authenticated
with check (
  event_type in ('page_view','product_open','whatsapp_click','search','gallery_open','occasion_filter','category_filter')
  and length(product_name) <= 180 and length(page_path) <= 300 and length(referrer) <= 500
  and length(client_id) <= 100 and length(session_id) <= 100
  and length(city) <= 120 and length(region) <= 120 and length(country) <= 80
  and length(device_type) <= 40 and length(browser) <= 60 and length(traffic_source) <= 120
  and length(utm_source) <= 120 and length(utm_medium) <= 120 and length(utm_campaign) <= 180
  and length(entry_path) <= 300 and length(event_context) <= 80
);

create index if not exists site_metrics_events_created_idx on public.site_metrics_events (created_at desc);
create index if not exists site_metrics_events_city_created_idx on public.site_metrics_events (city, created_at desc);
create index if not exists site_metrics_events_source_created_idx on public.site_metrics_events (traffic_source, created_at desc);
