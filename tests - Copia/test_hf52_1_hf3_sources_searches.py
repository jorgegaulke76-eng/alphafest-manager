from datetime import datetime, timezone
from pathlib import Path
import site_metrics_service as sm


def test_hf52_1_hf3_summary_sources_and_searches(monkeypatch):
    rows = {
        'page_view': [
            {'created_at':'2026-09-08T11:00:00+00:00','session_id':'s1','client_id':'c1','product_name':'','referrer':'https://www.google.com/search?q=alpha'},
            {'created_at':'2026-09-08T12:00:00+00:00','session_id':'s2','client_id':'c2','product_name':'','referrer':''},
        ],
        'product_open': [],
        'whatsapp_click': [],
        'search': [
            {'created_at':'2026-09-08T12:10:00+00:00','session_id':'s2','client_id':'c2','product_name':'caneca','referrer':''},
            {'created_at':'2026-09-08T12:20:00+00:00','session_id':'s2','client_id':'c2','product_name':'caneca','referrer':''},
            {'created_at':'2026-09-08T12:30:00+00:00','session_id':'s2','client_id':'c2','product_name':'balão','referrer':''},
        ],
    }
    monkeypatch.setattr(sm, '_rows', lambda event_type, since, limit=5000: rows[event_type])
    monkeypatch.setattr(sm, '_count', lambda event_type, since=None: sum(1 for r in rows.get(event_type, []) if sm._row_at_or_after(r, since)))
    out = sm.dashboard_summary(datetime(2026,9,8,13,0,tzinfo=timezone.utc))
    assert ('Google', 1) in out['traffic_sources']
    assert ('Direto', 1) in out['traffic_sources']
    assert out['top_search_terms'][0] == ('caneca', 2)
    assert out['searches_30d'] == 3


def test_hf52_1_hf3_tracking_and_ui_contract():
    service = Path('site_metrics_service.py').read_text(encoding='utf-8')
    app = Path('app.py').read_text(encoding='utf-8')
    sql = Path('SUPABASE_SITE_METRICS_HF52_1_HF3.sql').read_text(encoding='utf-8')
    assert "send('search',term)" in service
    assert "el.id==='search'" in service
    assert 'Origem dos acessos · 30 dias' in app
    assert 'Termos mais buscados no site · 30 dias' in app
    assert "'search'" in sql
