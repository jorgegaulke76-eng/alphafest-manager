"""HF52.1 — métricas privadas do site AlphaFest.

O site público envia apenas eventos comerciais mínimos para uma tabela dedicada
no Supabase. A tabela deve ter política de INSERT público e nenhuma política de
SELECT para anon. O Manager lê os dados somente com credencial de servidor.
"""
from __future__ import annotations

import html
import json
import os
import re
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
DASHBOARD_EVENT_TYPES = ("page_view", "product_open", "whatsapp_click", "search", "gallery_open", "occasion_filter", "category_filter")


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
    if not enabled or not page or not tracking_available() or 'id="alphafest-site-metrics"' in page:
        return page
    cfg = public_config()
    js_cfg = json.dumps(cfg, ensure_ascii=False)
    script = r"""<script id="alphafest-site-metrics">
(function(){
  const CFG=__CFG__;
  if(!CFG.url||!CFG.key||location.protocol==='file:') return;
  const endpoint=CFG.url+'/rest/v1/site_metrics_events';
  function uid(storage,key){
    try{let v=storage.getItem(key); if(v) return v; v=(crypto&&crypto.randomUUID)?crypto.randomUUID():String(Date.now())+'-'+Math.random().toString(16).slice(2); storage.setItem(key,v); return v;}catch(e){return '';}
  }
  function clip(v,n){return String(v||'').replace(/\s+/g,' ').trim().slice(0,n);}
  function browserName(){
    const ua=navigator.userAgent||'';
    if(/Edg\//.test(ua)) return 'Edge';
    if(/OPR\//.test(ua)) return 'Opera';
    if(/Firefox\//.test(ua)) return 'Firefox';
    if(/Chrome\//.test(ua)) return 'Chrome';
    if(/Safari\//.test(ua)) return 'Safari';
    return 'Outro';
  }
  function deviceType(){
    const ua=(navigator.userAgent||'').toLowerCase();
    if(/ipad|tablet/.test(ua)) return 'Tablet';
    if(/mobi|android|iphone|ipod/.test(ua) || Math.min(screen.width||9999,screen.height||9999)<700) return 'Celular';
    return 'Computador';
  }
  function sourceName(){
    const params=new URLSearchParams(location.search);
    const utm=clip(params.get('utm_source'),120);
    if(utm) return utm;
    const raw=document.referrer||'';
    if(!raw) return 'Direto';
    try{
      const host=(new URL(raw)).hostname.toLowerCase().replace(/^www\./,'');
      if(host.includes('google.')) return 'Google';
      if(host.endsWith('instagram.com')) return 'Instagram';
      if(host.endsWith('facebook.com')||host.endsWith('fb.com')) return 'Facebook';
      if(host.endsWith('tiktok.com')) return 'TikTok';
      if(host.endsWith('pinterest.com')) return 'Pinterest';
      if(host.endsWith('youtube.com')||host==='youtu.be') return 'YouTube';
      if(host.includes('whatsapp')||host==='wa.me') return 'WhatsApp';
      if(host.endsWith('alphafest.com.br')) return 'Navegação interna';
      return host||'Outros';
    }catch(e){return 'Outros';}
  }
  const clientId=uid(localStorage,'af_client_id_v1');
  const sessionId=uid(sessionStorage,'af_session_id_v1');
  // HF65.24.52: caminhos e origem NÃO incluem query string nem fragmentos.
  // Links recebidos podem carregar email, telefone ou tokens em parâmetros
  // arbitrários, que não são necessários para entender oportunidades.
  function safePath(raw){
    const base=String(raw||'/').split(/[?#]/,1)[0]||'/';
    return clip(base,300);
  }
  function safeReferrer(){
    try{
      const raw=document.referrer||'';
      if(!raw) return '';
      const u=new URL(raw);
      if(u.protocol!=='https:' && u.protocol!=='http:') return '';
      // O domínio basta para identificar o canal; caminhos externos podem conter dados privados.
      return clip(u.origin,500);
    }catch(e){return '';}
  }
  let entryPath=safePath(location.pathname);
  try{
    // Chave nova para não reutilizar o valor antigo, que continha a URL completa.
    entryPath=safePath(sessionStorage.getItem('af_entry_path_v52')||entryPath);
    sessionStorage.setItem('af_entry_path_v52',entryPath);
  }catch(e){}
  const qs=new URLSearchParams(location.search);
  // HF65.24.52: mantém a atribuição UTM apenas dentro da sessão atual.
  // Uma nova campanha explícita substitui a anterior. Não armazena dados pessoais.
  const utm={source:clip(qs.get('utm_source'),120),medium:clip(qs.get('utm_medium'),120),campaign:clip(qs.get('utm_campaign'),180)};
  try {
    const stored=JSON.parse(sessionStorage.getItem('af_utm_v52')||'{}');
    if(utm.source||utm.medium||utm.campaign){
      sessionStorage.setItem('af_utm_v52',JSON.stringify(utm));
    } else {
      utm.source=clip(stored.source,120);utm.medium=clip(stored.medium,120);utm.campaign=clip(stored.campaign,180);
    }
  } catch(e) {}
  const baseMeta={
    device_type:deviceType(), browser:browserName(), traffic_source:utm.source||sourceName(),
    utm_source:utm.source, utm_medium:utm.medium, utm_campaign:utm.campaign,
    entry_path:clip(entryPath,300)
  };
  // HF65.24.32: nunca bloquear a medição à espera de geolocalização.
  // A consulta geográfica é opcional; os cliques para WhatsApp precisam
  // iniciar seu POST imediatamente, antes de abrir outra janela.
  let geoCache={city:'',region:'',country:''};
  try{
    fetch('/__af_geo',{cache:'no-store',credentials:'same-origin'})
      .then(r=>r.ok?r.json():{})
      .then(g=>{geoCache={city:clip(g.city,120),region:clip(g.region,120),country:clip(g.country,80)};})
      .catch(function(){});
  }catch(e){}
  function send(type, product, context){
    const payload=Object.assign({},baseMeta,geoCache,{
      event_type:type,product_name:clip(product,180),page_path:safePath(location.pathname),referrer:safeReferrer(),
      client_id:clientId,session_id:sessionId,event_context:clip(context,80)
    });
    const headers={'apikey':CFG.key,'Content-Type':'application/json','Prefer':'return=minimal'};
    if(!CFG.key.startsWith('sb_publishable_')) headers['Authorization']='Bearer '+CFG.key;
    // keepalive permite ao navegador concluir requisições mesmo após abrir WhatsApp.
    try{fetch(endpoint,{method:'POST',headers:headers,body:JSON.stringify(payload),keepalive:true,mode:'cors'}).catch(function(){});}catch(e){}
  }
  window.__alphafestMetricsReady=true;
  // Eventos internos explicitamente identificados, sem conteúdo de mensagem ou dados pessoais.
  window.addEventListener('alphafest:metric',function(ev){
    const d=(ev&&ev.detail)||{};
    if(d.type==='whatsapp_click') send('whatsapp_click',clip(d.product,180),clip(d.context,80));
    if(d.type==='product_open') send('product_open',clip(d.product,180),clip(d.context,80));
  });
  send('page_view','','page');
  // A ficha de campanha pode ter aberto antes da inicialização deste rastreador.
  // Registra a abertura direta uma única vez sem depender de eventos anteriores.
  try {
    const slug=qs.get('produto')||'';
    if(/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) {
      const cards=[...document.querySelectorAll('.product-card[data-product]')];
      const product=cards.find(c=>c.dataset.product===slug) ||
        cards.find(c=>(c.dataset.productAliases||'').split(/\s+/).includes(slug));
      if(product) send('product_open',product.dataset.detailName||'','campaign_product');
    }
  } catch(e) {}
  let searchTimer=null, lastSearch='';
  function scheduleSearch(value){
    clearTimeout(searchTimer);
    const term=clip(value,180);
    if(term.length<2) return;
    searchTimer=setTimeout(function(){
      const key=term.toLocaleLowerCase('pt-BR');
      if(key===lastSearch) return;
      lastSearch=key;
      send('search',term,'site_search');
    },900);
  }
  document.addEventListener('input',function(ev){
    const el=ev.target;
    if(el && (el.id==='search' || el.id==='hf48-header-search-input')) scheduleSearch(el.value);
  },true);
  document.addEventListener('change',function(ev){
    const el=ev.target;
    if(!el) return;
    if(el.id==='gallery-occasion' && el.value && el.value!=='todos') send('occasion_filter',el.options[el.selectedIndex]?.textContent||el.value,'gallery');
    if(el.id==='gallery-cat' && el.value && el.value!=='todos') send('category_filter',el.options[el.selectedIndex]?.textContent||el.value,'gallery');
  },true);
  document.addEventListener('click',function(ev){
    const t=ev.target.closest ? ev.target.closest('a,button,.product-card,.product-related-card') : null;
    if(!t) return;
    const wa=t.closest && t.closest('a[href*="wa.me"],a[href*="api.whatsapp.com"],a[href*="whatsapp.com/send"]');
    if(wa){
      const galleryCard=wa.closest('.gallery-card');
      const galleryName=galleryCard&&galleryCard.querySelector('h3')?galleryCard.querySelector('h3').textContent.trim():'';
      const modal=document.getElementById('product-detail-name');
      const name=galleryName||(modal&&modal.textContent?modal.textContent.trim():'');
      send('whatsapp_click',name,galleryCard?'gallery':'site');
      return;
    }
    const photo=t.closest && t.closest('.gallery-photo-open');
    if(photo){send('gallery_open',photo.dataset.galleryTitle||photo.querySelector('img')?.alt||'','gallery');return;}
    const card=t.closest && t.closest('.product-card');
    if(card){send('product_open',(card.dataset.detailName||card.querySelector('h3')?.textContent||'').trim(),'product');return;}
    const car=t.closest && t.closest('[data-hf50-product]');
    if(car){send('product_open',(car.getAttribute('data-hf50-product')||'').trim(),'product');return;}
    const rel=t.closest && t.closest('.product-related-card');
    if(rel){send('product_open',(rel.textContent||'').trim(),'related_product');}
  },true);
})();
</script>
""".replace('__CFG__', js_cfg)
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
        "select": "product_name,created_at,referrer,page_path,client_id,session_id,city,region,country,device_type,browser,traffic_source,utm_source,utm_medium,utm_campaign,entry_path,event_context",
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
            ("select", "event_type,product_name,created_at,referrer,page_path,client_id,session_id,city,region,country,device_type,browser,traffic_source,utm_source,utm_medium,utm_campaign,entry_path,event_context"),
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


def _rows_since(rows: Iterable[dict[str, Any]], since: datetime) -> list[dict[str, Any]]:
    return [x for x in rows if _row_at_or_after(x, since)]


def _timeline(rows: Iterable[dict[str, Any]], *, mode: str, start: datetime, end: datetime) -> list[dict[str, Any]]:
    tz = ZoneInfo("America/Sao_Paulo")
    event_types = ("page_view", "product_open", "whatsapp_click")
    counters: dict[str, Counter] = {e: Counter() for e in event_types}
    for row in rows:
        et = str(row.get("event_type") or "").strip()
        if et not in counters or not _row_at_or_after(row, start):
            continue
        raw = str(row.get("created_at") or "").strip()
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            local = dt.astimezone(tz)
        except Exception:
            continue
        if local.astimezone(timezone.utc) > end.astimezone(timezone.utc):
            continue
        if mode == "day": key = local.strftime("%d/%m")
        elif mode == "month": key = local.strftime("%Y-%m")
        else: key = local.strftime("%Y")
        counters[et][key] += 1
    labels: list[str] = []
    if mode == "day":
        cur = start.astimezone(tz).date(); finish = end.astimezone(tz).date()
        while cur <= finish:
            labels.append(cur.strftime("%d/%m")); cur += timedelta(days=1)
    elif mode == "month":
        cur = start.astimezone(tz).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        finish = end.astimezone(tz).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        while cur <= finish:
            labels.append(cur.strftime("%Y-%m")); cur = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
    else:
        labels = [str(y) for y in range(start.astimezone(tz).year, end.astimezone(tz).year + 1)]
    return [{"Período": label, "Acessos": counters["page_view"].get(label,0), "Produtos": counters["product_open"].get(label,0), "WhatsApp": counters["whatsapp_click"].get(label,0)} for label in labels]


# HF65.24.31 — separação transparente de acessos técnicos por caminho.
# Não classificar robôs por inferência: sem user-agent/identificação verificada,
# podemos apenas separar URLs evidentemente técnicas, sem afirmar que foram bots.
def _normalized_page_path(value: Any) -> str:
    from urllib.parse import unquote
    raw = str(value or '/').split('?', 1)[0].split('#', 1)[0].strip()
    try:
        raw = unquote(raw)
    except Exception:
        pass
    path = '/' + raw.lstrip('/')
    path = re.sub(r'/+', '/', path)
    return path if path == '/' else path.rstrip('/') + '/'


def _technical_page_path(value: Any) -> bool:
    path = _normalized_page_path(value).lower()
    basename = path.strip('/').split('/')[-1]
    if basename in {'robots.txt', 'ads.txt', 'favicon.ico', 'manifest.webmanifest', 'site.webmanifest',
                    'manifest.json', 'sitemap.xml', 'news-sitemap.xml', 'news_sitemap.xml',
                    'sitemap_index.xml', 'service-worker.js', 'sw.js', 'offline.html',
                    'apple-touch-icon.png', 'browserconfig.xml', 'security.txt'}:
        return True
    if basename.endswith(('.xml', '.json', '.txt', '.webmanifest', '.map', '.js', '.css', '.png', '.jpg', '.jpeg', '.webp', '.svg', '.ico')):
        return True
    if path.startswith(('/__af_', '/.well-known/', '/static/', '/assets/', '/_next/')):
        return True
    return False


def _page_friendly_name(path: str) -> str:
    p = _normalized_page_path(path)
    known = {'/': 'Página inicial', '/contato/': 'Contato', '/empresas/': 'Para Empresas',
             '/novidades/': 'Novidades & Ofertas', '/dicas/': 'Dicas & Inspirações',
             '/produtos/': 'Produtos', '/galeria/': 'Galeria', '/quem-somos/': 'Quem Somos',
             '/servicos/': 'Serviços', '/categorias/': 'Categorias'}
    if p in known: return known[p]
    if p.startswith('/novidades/pagina-'):
        return 'Novidades & Ofertas · ' + p.strip('/').split('/')[-1].replace('pagina-', 'página ')
    if p.startswith('/dicas/'):
        slug = p.strip('/').split('/')[-1]
        return 'Dicas · ' + slug.replace('-', ' ').capitalize()
    return p


def _compare_window(rows: list[dict[str, Any]], start: datetime, end: datetime) -> dict[str, Any]:
    """Métricas de uma janela [início, fim), com fim exclusivo.

    Só considera URLs técnicas no contador bruto, não nas sessões comerciais.
    Os eventos WhatsApp são associados ao canal da primeira visita naquela janela,
    sem atribuir venda, pessoa ou conversão a produto.
    """
    scoped=[]
    for row in rows:
        raw=str(row.get('created_at') or '').strip()
        try:
            timestamp=datetime.fromisoformat(raw.replace('Z','+00:00'))
            if timestamp.tzinfo is None: timestamp=timestamp.replace(tzinfo=timezone.utc)
            timestamp=timestamp.astimezone(timezone.utc)
        except (ValueError,TypeError):
            continue
        if start <= timestamp < end:
            scoped.append(row)
    pages=[r for r in scoped if r.get('event_type') == 'page_view' and not _technical_page_path(r.get('page_path'))]
    products=[r for r in scoped if r.get('event_type') == 'product_open']
    whatsapp=[r for r in scoped if r.get('event_type') == 'whatsapp_click']
    first={}
    for row in sorted(pages,key=lambda x: str(x.get('created_at') or '')):
        sid=str(row.get('session_id') or '').strip()
        if sid and sid not in first: first[sid]=row
    wa_sids={str(r.get('session_id') or '').strip() for r in whatsapp if r.get('session_id')}
    channel_sessions=Counter()
    channel_wa=Counter()
    for sid,row in first.items():
        source=(str(row.get('traffic_source') or '').strip()
                or _traffic_source(str(row.get('referrer') or '')) or 'Não informado')
        channel_sessions[source]+=1
        if sid in wa_sids: channel_wa[source]+=1
    return {'visitas':len(pages),'produtos':len(products),'whatsapp':len(whatsapp),
            'sessoes':len(first),'sessoes_whatsapp':len(set(first)&wa_sids),
            'carrinho':sum(r.get('event_context')=='carrinho' for r in whatsapp),
            'empresas':sum(r.get('event_context')=='empresas' for r in whatsapp),
            'canais':dict(channel_sessions),'canais_whatsapp':dict(channel_wa),
            'produtos_abertos':dict(Counter(str(r.get('product_name') or '').strip() for r in products if r.get('product_name')))}


def _compare_periods(rows: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    periods={}
    for days in (7,30):
        cut=now-timedelta(days=days)
        past=cut-timedelta(days=days)
        periods[f'{days}d']={'atual':_compare_window(rows,cut,now),
                             'anterior':_compare_window(rows,past,cut),
                             'dias':days}
    return periods


# HF65.24.37 — associação por sessão e campanha UTM, sem venda presumida.
def _campaign_opportunities(rows: list[dict[str, Any]], start: datetime, end: datetime) -> list[dict[str, Any]]:
    """Agrupa a primeira campanha UTM identificada por sessão na janela.

    Um acesso direto anterior ao link UTM não elimina a campanha encontrada
    posteriormente. Somente cliques WhatsApp após essa primeira identificação
    entram na contagem. Não se inferem mensagens enviadas ou vendas.
    """
    selected = []
    for row in rows:
        try:
            t = datetime.fromisoformat(str(row.get("created_at") or "").replace("Z", "+00:00"))
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            t = t.astimezone(timezone.utc)
        except (ValueError, TypeError):
            continue
        if start <= t < end:
            selected.append((t, row))
    first_utm = {}
    for t, row in sorted(selected, key=lambda item: item[0]):
        if row.get("event_type") != "page_view" or _technical_page_path(row.get("page_path")):
            continue
        sid = str(row.get("session_id") or "").strip()
        campaign = str(row.get("utm_campaign") or "").strip()
        if sid and campaign and sid not in first_utm:
            first_utm[sid] = (t, row)
    wa_by_sid = Counter()
    for t, row in selected:
        sid = str(row.get("session_id") or "").strip()
        if (row.get("event_type") == "whatsapp_click"
                and sid in first_utm and t >= first_utm[sid][0]):
            wa_by_sid[sid] += 1
    hits = Counter()
    wa_sessions = Counter()
    wa_clicks = Counter()
    for sid, (_, row) in first_utm.items():
        name = str(row.get("utm_campaign") or "").strip()[:180]
        src = str(row.get("utm_source") or row.get("traffic_source") or "Não informado").strip()[:120]
        key = (name, src)
        hits[key] += 1
        if wa_by_sid[sid]:
            wa_sessions[key] += 1
            wa_clicks[key] += wa_by_sid[sid]
    return [{"campanha": name, "canal": source, "sessoes": qty,
             "sessoes_whatsapp": wa_sessions[(name, source)],
             "cliques_whatsapp": wa_clicks[(name, source)],
             "percentual": _pct(wa_sessions[(name, source)], qty)}
            for (name, source), qty in sorted(
                hits.items(), key=lambda z: (-z[1], z[0][0].casefold(), z[0][1].casefold())
            )]


def dashboard_summary(now: datetime | None = None) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None: now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    local_now = now.astimezone(ZoneInfo("America/Sao_Paulo"))
    dtoday = local_now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    d7, d30, d3y = now-timedelta(days=7), now-timedelta(days=30), now-timedelta(days=1095)
    all_rows = _dashboard_rows(d3y, now)
    page_rows = _event_rows(all_rows, "page_view"); product_rows = _event_rows(all_rows, "product_open"); wa_rows = _event_rows(all_rows, "whatsapp_click")
    search_rows = _event_rows(all_rows, "search"); gallery_rows = _event_rows(all_rows, "gallery_open"); occasion_rows = _event_rows(all_rows, "occasion_filter")
    page_30, product_30, wa_30 = _rows_since(page_rows,d30), _rows_since(product_rows,d30), _rows_since(wa_rows,d30)
    search_30, gallery_30, occasion_30 = _rows_since(search_rows,d30), _rows_since(gallery_rows,d30), _rows_since(occasion_rows,d30)
    products=Counter(str(x.get("product_name") or "").strip() for x in product_30 if str(x.get("product_name") or "").strip())
    wa_products=Counter(str(x.get("product_name") or "").strip() for x in wa_30 if str(x.get("product_name") or "").strip())
    search_terms=Counter(str(x.get("product_name") or "").strip() for x in search_30 if str(x.get("product_name") or "").strip())
    gallery_items=Counter(str(x.get("product_name") or "").strip() for x in gallery_30 if str(x.get("product_name") or "").strip())
    occasions=Counter(str(x.get("product_name") or "").strip() for x in occasion_30 if str(x.get("product_name") or "").strip())
    # Atribuição por caminho e contexto sem armazenar dados preenchidos pelo cliente.
    raw_page_paths=Counter(_normalized_page_path(x.get('page_path')) for x in page_30)
    technical_pages=Counter({path:n for path,n in raw_page_paths.items() if _technical_page_path(path)})
    page_paths=Counter({path:n for path,n in raw_page_paths.items() if not _technical_page_path(path)})
    qualified_page_30=[x for x in page_30 if not _technical_page_path(x.get('page_path'))]
    commercial_sessions={str(x.get('session_id') or '') for x in qualified_page_30 if str(x.get('session_id') or '')}
    commercial_visitors={str(x.get('client_id') or '') for x in qualified_page_30 if str(x.get('client_id') or '')}
    business_page_views=sum(n for path,n in page_paths.items() if path.startswith('/empresas/'))
    news_page_views=sum(n for path,n in page_paths.items() if path.startswith('/novidades/'))
    editorial_page_views=sum(n for path,n in page_paths.items() if path.startswith('/dicas/'))
    quote_clicks=sum(1 for x in wa_30 if str(x.get('event_context') or '')=='carrinho')
    business_clicks=sum(1 for x in wa_30 if str(x.get('event_context') or '')=='empresas')
    wa_by_path=Counter(_normalized_page_path(x.get('page_path')) for x in wa_30 if not _technical_page_path(x.get('page_path')))

    traffic_sources=Counter((str(x.get('traffic_source') or '')).strip() or _traffic_source(str(x.get('referrer') or '')) for x in page_30)
    cities=Counter(str(x.get("city") or "").strip() for x in page_30 if str(x.get("city") or "").strip())
    regions=Counter(str(x.get("region") or "").strip() for x in page_30 if str(x.get("region") or "").strip())
    devices=Counter(str(x.get("device_type") or "").strip() for x in page_30 if str(x.get("device_type") or "").strip())
    browsers=Counter(str(x.get("browser") or "").strip() for x in page_30 if str(x.get("browser") or "").strip())
    campaigns=Counter(str(x.get("utm_campaign") or "").strip() for x in page_30 if str(x.get("utm_campaign") or "").strip())
    wa_contexts=Counter(str(x.get("event_context") or "").strip() for x in wa_30 if str(x.get("event_context") or "").strip())
    # HF65.24.34: perfil agregado da primeira visita por sessão, não por page_view.
    # Não identifica indivíduos e não infere sexo/gênero a partir de navegação.
    first_by_session={}
    for item in sorted(qualified_page_30, key=lambda x: str(x.get('created_at') or '')):
        sid=str(item.get('session_id') or '').strip()
        if sid and sid not in first_by_session:
            first_by_session[sid]=item
    profile_rows=list(first_by_session.values())
    def profile_counter(field, fallback='Não informado'):
        return Counter(str(row.get(field) or '').strip() or fallback for row in profile_rows)
    profile_sources=Counter(
        (str(row.get('traffic_source') or '').strip()
         or _traffic_source(str(row.get('referrer') or '')) or 'Não informado')
        for row in profile_rows)
    profile_cities=profile_counter('city')
    profile_regions=profile_counter('region')
    profile_countries=profile_counter('country')
    profile_devices=profile_counter('device_type')
    profile_browsers=profile_counter('browser')
    known_city_sessions=sum(v for k,v in profile_cities.items() if k != 'Não informado')
    # HF65.24.35: oportunidades por interesse agregado; sem atribuir
    # itens do carrinho a produtos nem transformar cliques em vendas.
    generic_wa_prefixes = ('orçamento com ', 'orçamento corporativo')
    wa_named = Counter(name for name, qty in wa_products.items()
                       for _ in range(qty)
                       if not name.casefold().startswith(generic_wa_prefixes))
    product_opportunities = []
    for name in sorted(set(products) | set(wa_named), key=str.casefold):
        opens, direct = products[name], wa_named[name]
        if direct >= 2 and opens >= 3:
            status = 'Interesse recorrente'
        elif direct:
            status = 'Clique direto identificado'
        elif opens >= 3:
            status = 'Visualizações recorrentes'
        else:
            status = 'Amostra inicial'
        product_opportunities.append({
            'produto': name, 'aberturas': opens, 'cliques_diretos': direct,
            'sinal': status
        })
    product_opportunities.sort(key=lambda x: (-x['cliques_diretos'], -x['aberturas'], x['produto'].casefold()))

    # Origem da primeira página da sessão e presença de clique em WhatsApp
    # na MESMA sessão; associação observada, não causalidade/atribuição.
    # Uma sessão é contada uma vez em cada indicador.
    wa_session_ids={str(x.get('session_id') or '').strip() for x in wa_30 if str(x.get('session_id') or '').strip()}
    channel_opportunities=[]
    channel_sessions=Counter()
    channel_contacts=Counter()
    for sid, row in first_by_session.items():
        source=(str(row.get('traffic_source') or '').strip()
                or _traffic_source(str(row.get('referrer') or '')) or 'Não informado')
        channel_sessions[source] += 1
        if sid in wa_session_ids:
            channel_contacts[source] += 1
    for source, total in channel_sessions.most_common():
        contacts=channel_contacts[source]
        channel_opportunities.append({
            'canal':source, 'sessoes':total,'sessoes_whatsapp':contacts,
            'percentual':_pct(contacts,total)
        })
    sessions={str(x.get("session_id") or "") for x in page_30 if str(x.get("session_id") or "")}; visitors={str(x.get("client_id") or "") for x in page_30 if str(x.get("client_id") or "")}
    periods={}
    for key,since in (("today",dtoday),("7d",d7),("30d",d30)):
        ps=_session_ids(page_rows,since); prs=_session_ids(product_rows,since); ws=_session_ids(wa_rows,since)
        periods[key]={"pageviews":_event_count(page_rows,since),"products":_event_count(product_rows,since),"whatsapp":_event_count(wa_rows,since),"sessions":len(ps),"product_sessions":len(prs),"whatsapp_sessions":len(ws),"conv_product":_pct(len(prs),len(ps)),"conv_whatsapp":_pct(len(ws),len(ps)),"conv_product_to_whatsapp":_pct(len(ws),len(prs))}
    month_start=(local_now.replace(day=1,hour=0,minute=0,second=0,microsecond=0)-timedelta(days=335)).replace(day=1).astimezone(timezone.utc)
    year_start=local_now.replace(month=1,day=1,hour=0,minute=0,second=0,microsecond=0).astimezone(timezone.utc)
    return {
      "pageviews_today":periods["today"]["pageviews"],"pageviews_7d":periods["7d"]["pageviews"],"pageviews_30d":periods["30d"]["pageviews"],
      "product_today":periods["today"]["products"],"product_7d":periods["7d"]["products"],"product_30d":periods["30d"]["products"],
      "whatsapp_today":periods["today"]["whatsapp"],"whatsapp_7d":periods["7d"]["whatsapp"],"whatsapp_30d":periods["30d"]["whatsapp"],
      "sessions_30d":len(sessions),"visitors_30d":len(visitors),"periods":periods,"top_products":products.most_common(8),"top_whatsapp_products":wa_products.most_common(8),
      "top_search_terms":search_terms.most_common(10),"traffic_sources":traffic_sources.most_common(10),"top_cities":cities.most_common(10),"top_regions":regions.most_common(10),
      "devices":devices.most_common(10),"browsers":browsers.most_common(10),"top_campaigns":campaigns.most_common(10),"top_gallery":gallery_items.most_common(8),"top_occasions":occasions.most_common(10),
      "commercial_clicks_30d":{"cart":quote_clicks,"corporate":business_clicks},"commercial_pages_30d":{"corporate":business_page_views,"news":news_page_views,"tips":editorial_page_views},"top_pages_30d":page_paths.most_common(12),"top_whatsapp_pages_30d":wa_by_path.most_common(10),
      "technical_pageviews_30d":sum(technical_pages.values()),"commercial_pageviews_30d":sum(page_paths.values()),"top_technical_pages_30d":technical_pages.most_common(8),
      "commercial_sessions_30d":len(commercial_sessions),"commercial_visitors_30d":len(commercial_visitors),
      "audience_profile_30d":{"session_count":len(profile_rows),"known_city_sessions":known_city_sessions,
          "cities":profile_cities.most_common(12),"regions":profile_regions.most_common(12),
          "countries":profile_countries.most_common(12),"devices":profile_devices.most_common(12),
          "browsers":profile_browsers.most_common(12),"sources":profile_sources.most_common(12),
          "gender_available":False},
      "product_opportunities_30d":product_opportunities[:20],"channel_opportunities_30d":channel_opportunities[:20],
      "campaign_opportunities_30d":_campaign_opportunities(all_rows,d30,now)[:50],
      "campaign_opportunities_7d":_campaign_opportunities(all_rows,d7,now)[:50],
      "campaign_opportunities_prev_7d":_campaign_opportunities(all_rows,d7-timedelta(days=7),d7)[:50],
      "campaign_opportunities_prev_30d":_campaign_opportunities(all_rows,d30-timedelta(days=30),d30)[:50],
      "period_comparisons":_compare_periods(all_rows,now),
      "whatsapp_contexts":wa_contexts.most_common(10),"searches_30d":len(search_30),"daily_series":_timeline(all_rows,mode="day",start=d30,end=now),
      "monthly_series":_timeline(all_rows,mode="month",start=month_start,end=now),"yearly_series":_timeline(all_rows,mode="year",start=d3y,end=now),"current_year_series":_timeline(all_rows,mode="month",start=year_start,end=now)
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
