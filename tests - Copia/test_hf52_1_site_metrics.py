from pathlib import Path
import site_metrics_service as sm


def test_tracking_injection_has_three_events(monkeypatch):
    monkeypatch.setattr(sm, 'public_config', lambda: {'url':'https://example.supabase.co','key':'sb_publishable_test'})
    page=sm.inject_tracking('<html><body><a href="https://wa.me/55">x</a></body></html>')
    assert 'page_view' in page
    assert 'product_open' in page
    assert 'whatsapp_click' in page
    assert 'site_metrics_events' in page


def test_sql_is_insert_only_for_public():
    sql=Path('SUPABASE_SITE_METRICS_HF52_1.sql').read_text(encoding='utf-8').lower()
    assert 'grant insert' in sql
    assert 'revoke select' in sql
    assert 'create policy "public_insert_site_metrics"' in sql


def test_version_hf52_1_or_hotfix():
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip().startswith(('20.4.9-I8.13.5-HF52.', '20.4.9-I8.13.5-HF53.'))
