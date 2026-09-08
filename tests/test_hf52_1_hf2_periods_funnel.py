from datetime import datetime, timezone
from pathlib import Path
import site_metrics_service as sm


def test_hf52_1_hf2_dashboard_contract(monkeypatch):
    rows = {
        'page_view': [
            {'created_at':'2026-09-08T11:00:00+00:00','session_id':'s1','client_id':'c1','product_name':''},
            {'created_at':'2026-09-08T12:00:00+00:00','session_id':'s2','client_id':'c2','product_name':''},
        ],
        'product_open': [
            {'created_at':'2026-09-08T11:10:00+00:00','session_id':'s1','client_id':'c1','product_name':'Produto A'},
        ],
        'whatsapp_click': [
            {'created_at':'2026-09-08T11:20:00+00:00','session_id':'s1','client_id':'c1','product_name':'Produto A'},
        ],
    }
    monkeypatch.setattr(sm, '_rows', lambda event_type, since, limit=5000: rows[event_type])
    monkeypatch.setattr(sm, '_count', lambda event_type, since=None: sum(1 for r in rows[event_type] if sm._row_at_or_after(r, since)))
    out = sm.dashboard_summary(datetime(2026,9,8,13,0,tzinfo=timezone.utc))
    assert out['periods']['today']['pageviews'] == 2
    assert out['periods']['today']['products'] == 1
    assert out['periods']['today']['whatsapp'] == 1
    assert out['periods']['30d']['conv_product'] == 50.0
    assert out['periods']['30d']['conv_whatsapp'] == 50.0
    assert out['periods']['30d']['conv_product_to_whatsapp'] == 100.0


def test_hf52_1_hf2_ui_contract():
    app = Path('app.py').read_text(encoding='utf-8')
    assert 'Métricas privadas do Site · HF52.1-HF2' in app
    assert 'Resumo por período' in app
    assert 'Últimos 7 dias' in app
    assert 'Funil comercial por sessão' in app
    assert 'Acesso → Produto' in app
    assert 'Produto → WhatsApp' in app
