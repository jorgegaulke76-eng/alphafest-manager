"""HF52.1 — métricas privadas do site AlphaFest.

O site público envia apenas eventos comerciais mínimos para uma tabela dedicada
no Supabase. A tabela deve ter política de INSERT público e nenhuma política de
SELECT para anon. O Manager lê os dados somente com credencial de servidor.
"""
from __future__ import annotations

import html
import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from urllib.parse import urlparse
from typing import Any, Dict, Iterable

import requests
try:
    import streamlit as st
except Exception:  # permite testes/empacotamento fora do Streamlit
    st = None

TIMEOUT = 10
TABLE = "site_metrics_events"
DASHBOARD_PAGE_SIZE = 5000
DASHBOARD_EVENT_TYPES = ("page_view", "product_open", "whatsapp_click", "search")


def _secret(name: str) -> str:
    value = ""
    try:
        if st is not None:
            value = str(st.secrets.get(name, "") or "").strip()
    except Exception:
        pass
    return value or os.getenv(name, "").strip()


def public_config() -> Dict[str, str]:
    """Somente credenciais públicas/publishable podem ir para o HTML."""
    return {
        "url": _secret("SUPABASE_URL").rstrip("/"),
        "key": _secret("SUPABASE_KEY"),
    }


def server_config() -> Dict[str, str]:
    return {
        "url": _secret("SUPABASE_URL").rstrip("/"),
        "key": _secret("SUPABASE_SERVICE_KEY"),
    }


def tracking_available() -> bool:
    cfg = public_config()
    return bool(cfg["url"] and cfg["key"])


def inject_tracking(page: str, *, enabled: bool = True) -> str:
    if not enabled or not page or not tracking_available():
        return page
    cfg = public_config()
    js_cfg = json.dumps(cfg, ensure_ascii=False)
    script = r'''
<script id="alphafest-site-metrics">
(function(){
  const CFG=__CFG__;
  if(!CFG.url||!CFG.key||location.protocol==='file:') return;
  const endpoint=CFG.url+'/rest/v1/site_metrics_events';
  function uid(storage,key){
    try{let v=storage.getItem(key); if(v) return v; v=(crypto&&crypto.randomUUID)?crypto.randomUUID():String(Date.now())+'-'+Math.random().toString(16).slice(2); storage.setItem(key,v); return v;}catch(e){return '';}
  }
  const clientId=uid(localStorage,'af_client_id_v1');
  const sessionId=uid(sessionStorage,'af_session_id_v1');
  function send(type, product){
    const payload={event_type:type,product_name:(product||'').slice(0,180),page_path:(location.pathname+location.hash).slice(0,300),referrer:(document.referrer||'').slice(0,500),client_id:clientId,session_id:sessionId};
    const headers={'apikey':CFG.key,'Content-Type':'application/json','Prefer':'return=minimal'};
    if(!CFG.key.startsWith('sb_publishable_')) headers['Authorization']='Bearer '+CFG.key;
    try{fetch(endpoint,{method:'POST',headers:headers,body:JSON.stringify(payload),keepalive:true,mode:'cors'}).catch(function(){});}catch(e){}
  }
  send('page_view','');
  let searchTimer=null, lastSearch='';
  function scheduleSearch(value){
    clearTimeout(searchTimer);
    const term=(value||'').replace(/\s+/g,' ').trim().slice(0,180);
    if(term.length<2) return;
    searchTimer=setTimeout(function(){
      const key=term.toLocaleLowerCase('pt-BR');
      if(key===lastSearch) return;
      lastSearch=key;
      send('search',term);
    },900);
  }
  document.addEventListener('input',function(ev){
    const el=ev.target;
    if(el && (el.id==='search' || el.id==='hf48-header-search-input')) scheduleSearch(el.value);
  },true);
  document.addEventListener('click',function(ev){
    const t=ev.target.closest ? ev.target.closest('a,button,.product-card,.product-related-card') : null;
    if(!t) return;
    const wa=t.closest && t.closest('a[href*="wa.me"],a[href*="api.whatsapp.com"],a[href*="whatsapp.com/send"]');
    if(wa){
      const modal=document.getElementById('product-detail-name');
      send('whatsapp_click', modal && modal.textContent ? modal.textContent.trim() : '');
      return;
    }
    const card=t.closest && t.closest('.product-card');
    if(card){send('product_open',(card.dataset.detailName||card.querySelector('h3')?.textContent||'').trim());return;}
    const car=t.closest && t.closest('[data-hf50-product]');
    if(car){send('product_open',(car.getAttribute('data-hf50-product')||'').trim());return;}
    const rel=t.closest && t.closest('.product-related-card');
    if(rel){send('product_open',(rel.textContent||'').trim());}
  },true);
})();
</script>
'''.replace('__CFG__', js_cfg)
    if "</body>" in page:
        return page.replace("</body>", script + "</body>", 1)
    return page + script


def _headers_server() -> Dict[str, str]:
    cfg = server_config()
    key = cfg["key"]
    h = {"apikey": key, "Content-Type": "application/json"}
    if key and not key.startswith("sb_secret_"):
        h["Authorization"] = f"Bearer {key}"
    return h


def _count(event_type: str, since: datetime | None = None) -> int:
    cfg = server_config()
    if not cfg["url"] or not cfg["key"]:
        raise RuntimeError("Credencial de servidor do Supabase não configurada.")
    params = {"select": "id", "event_type": f"eq.{event_type}", "limit": "1"}
    if since is not None:
        params["created_at"] = "gte." + since.astimezone(timezone.utc).isoformat()
    r = requests.get(
        f"{cfg['url']}/rest/v1/{TABLE}",
        headers={**_headers_server(), "Prefer": "count=exact"},
        params=params,
        timeout=TIMEOUT,
    )
    if r.status_code == 404:
        raise LookupError("Tabela de métricas ainda não criada.")
    r.raise_for_status()
    cr = r.headers.get("Content-Range", "")
    try:
        return int(cr.rsplit("/", 1)[1])
    except Exception:
        return len(r.json() or [])


def _rows(event_type: str, since: datetime, limit: int = 5000) -> list[dict[str, Any]]:
    cfg = server_config()
    params = {
        "select": "product_name,created_at,referrer,page_path,client_id,session_id",
        "event_type": f"eq.{event_type}",
        "created_at": "gte." + since.astimezone(timezone.utc).isoformat(),
        "order": "created_at.desc",
        "limit": str(limit),
    }
    r = requests.get(f"{cfg['url']}/rest/v1/{TABLE}", headers=_headers_server(), params=params, timeout=TIMEOUT)
    if r.status_code == 404:
        raise LookupError("Tabela de métricas ainda não criada.")
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else []


def _dashboard_rows(since: datetime, until: datetime | None = None, page_size: int = DASHBOARD_PAGE_SIZE) -> list[dict[str, Any]]:
    """Busca os eventos usados pelo painel em uma única consulta paginada.

    HF21: substitui quatro leituras por tipo + nove consultas de contagem.
    A paginação mantém os totais exatos mesmo se o período ultrapassar 5 mil
    eventos. O limite superior fixa um snapshot consistente durante a leitura.
    """
    cfg = server_config()
    if not cfg["url"] or not cfg["key"]:
        raise RuntimeError("Credencial de servidor do Supabase não configurada.")
    until = (until or datetime.now(timezone.utc)).astimezone(timezone.utc)
    since = since.astimezone(timezone.utc)
    page_size = max(1, int(page_size or DASHBOARD_PAGE_SIZE))
    rows: list[dict[str, Any]] = []
    offset = 0
    event_filter = "in.(" + ",".join(DASHBOARD_EVENT_TYPES) + ")"
    while True:
        # Lista de tuplas preserva os dois filtros created_at do PostgREST.
        params = [
            ("select", "event_type,product_name,created_at,referrer,page_path,client_id,session_id"),
            ("event_type", event_filter),
            ("created_at", "gte." + since.isoformat()),
            ("created_at", "lte." + until.isoformat()),
            ("order", "created_at.asc,id.asc"),
            ("limit", str(page_size)),
            ("offset", str(offset)),
        ]
        r = requests.get(
            f"{cfg['url']}/rest/v1/{TABLE}",
            headers=_headers_server(),
            params=params,
            timeout=TIMEOUT,
        )
        if r.status_code == 404:
            raise LookupError("Tabela de métricas ainda não criada.")
        r.raise_for_status()
        data = r.json()
        page = data if isinstance(data, list) else []
        rows.extend(page)
        if len(page) < page_size:
            break
        offset += len(page)
    return rows


def _event_rows(rows: Iterable[dict[str, Any]], event_type: str) -> list[dict[str, Any]]:
    return [x for x in rows if str(x.get("event_type") or "").strip() == event_type]


def _event_count(rows: Iterable[dict[str, Any]], since: datetime) -> int:
    return sum(1 for x in rows if _row_at_or_after(x, since))


def _row_at_or_after(row: dict[str, Any], since: datetime) -> bool:
    raw = str(row.get("created_at") or "").strip()
    if not raw:
        return False
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc) >= since.astimezone(timezone.utc)
    except Exception:
        return False


def _session_ids(rows: Iterable[dict[str, Any]], since: datetime) -> set[str]:
    return {
        str(x.get("session_id") or "").strip()
        for x in rows
        if _row_at_or_after(x, since) and str(x.get("session_id") or "").strip()
    }


def _pct(num: int, den: int) -> float:
    return round((num / den) * 100, 1) if den else 0.0


def _traffic_source(referrer: str) -> str:
    raw = str(referrer or "").strip()
    if not raw:
        return "Direto"
    try:
        host = (urlparse(raw).hostname or "").lower().removeprefix("www.")
    except Exception:
        host = raw.lower()
    if "google." in host:
        return "Google"
    if host.endswith("instagram.com"):
        return "Instagram"
    if host.endswith("facebook.com") or host.endswith("fb.com"):
        return "Facebook"
    if host.endswith("tiktok.com"):
        return "TikTok"
    if host.endswith("pinterest.com"):
        return "Pinterest"
    if host.endswith("youtube.com") or host.endswith("youtu.be"):
        return "YouTube"
    if "whatsapp" in host or host == "wa.me":
        return "WhatsApp"
    if host.endswith("alphafest.com.br"):
        return "Navegação interna"
    return host or "Outros"


def dashboard_summary(now: datetime | None = None) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)

    # "Hoje" segue o dia civil da operação AlphaFest (America/Sao_Paulo).
    local_now = now.astimezone(ZoneInfo("America/Sao_Paulo"))
    today_local = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    dtoday = today_local.astimezone(timezone.utc)
    d7 = now - timedelta(days=7)
    d30 = now - timedelta(days=30)

    # HF21: um snapshot paginado único alimenta contagens, funil e rankings.
    all_rows = _dashboard_rows(d30, now)
    page_rows = _event_rows(all_rows, "page_view")
    product_rows = _event_rows(all_rows, "product_open")
    wa_rows = _event_rows(all_rows, "whatsapp_click")
    search_rows = _event_rows(all_rows, "search")

    products = Counter(str(x.get("product_name") or "").strip() for x in product_rows if str(x.get("product_name") or "").strip())
    wa_products = Counter(str(x.get("product_name") or "").strip() for x in wa_rows if str(x.get("product_name") or "").strip())
    search_terms = Counter(str(x.get("product_name") or "").strip() for x in search_rows if str(x.get("product_name") or "").strip())
    traffic_sources = Counter(_traffic_source(str(x.get("referrer") or "")) for x in page_rows)
    sessions = {str(x.get("session_id") or "") for x in page_rows if str(x.get("session_id") or "")}
    visitors = {str(x.get("client_id") or "") for x in page_rows if str(x.get("client_id") or "")}

    periods = {}
    for key, since in (("today", dtoday), ("7d", d7), ("30d", d30)):
        page_sessions = _session_ids(page_rows, since)
        product_sessions = _session_ids(product_rows, since)
        wa_sessions = _session_ids(wa_rows, since)
        periods[key] = {
            "pageviews": _event_count(page_rows, since),
            "products": _event_count(product_rows, since),
            "whatsapp": _event_count(wa_rows, since),
            "sessions": len(page_sessions),
            "product_sessions": len(product_sessions),
            "whatsapp_sessions": len(wa_sessions),
            "conv_product": _pct(len(product_sessions), len(page_sessions)),
            "conv_whatsapp": _pct(len(wa_sessions), len(page_sessions)),
            "conv_product_to_whatsapp": _pct(len(wa_sessions), len(product_sessions)),
        }

    return {
        "pageviews_today": periods["today"]["pageviews"],
        "pageviews_7d": periods["7d"]["pageviews"],
        "pageviews_30d": periods["30d"]["pageviews"],
        "product_today": periods["today"]["products"],
        "product_7d": periods["7d"]["products"],
        "product_30d": periods["30d"]["products"],
        "whatsapp_today": periods["today"]["whatsapp"],
        "whatsapp_7d": periods["7d"]["whatsapp"],
        "whatsapp_30d": periods["30d"]["whatsapp"],
        "sessions_30d": len(sessions),
        "visitors_30d": len(visitors),
        "periods": periods,
        "top_products": products.most_common(8),
        "top_whatsapp_products": wa_products.most_common(8),
        "top_search_terms": search_terms.most_common(10),
        "traffic_sources": traffic_sources.most_common(10),
        "searches_30d": len(search_rows),
    }


# HF21 — o painel automático roda a cada 30s; um cache curto impede que outros
# reruns da mesma sessão (por exemplo o Piloto Automático de Marketing) repitam a
# consulta imediatamente. O botão "Atualizar agora" limpa este cache explicitamente.
if st is not None:
    @st.cache_data(ttl=25, show_spinner=False)
    def dashboard_summary_cached() -> Dict[str, Any]:
        return dashboard_summary()

    def clear_dashboard_summary_cache() -> None:
        dashboard_summary_cached.clear()
else:
    def dashboard_summary_cached() -> Dict[str, Any]:
        return dashboard_summary()

    def clear_dashboard_summary_cache() -> None:
        return None
