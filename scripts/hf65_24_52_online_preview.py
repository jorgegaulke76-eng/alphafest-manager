"""Build a SAFE, public, static HF65.24.52 preview for GitHub Pages.

Source data: public AlphaFest vitrine HTML; no private Manager data/credentials.
Preview behavior: HF52 product modal, cart and UTM code, with all metric POSTs
kept in browser memory and outbound WhatsApp intercepted before navigation.
This is NOT a live publication to alphafest.com.br or Cloudflare.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from site_carrinho_orcamento_service import CSS as CART_CSS
from site_carrinho_orcamento_service import JS as CART_JS
import site_metrics_service as metrics
from hf65_24_52_browser_preview import (
    PRODUCT_NAME, PRODUCT_SLUG, build_public_preview
)

OUT = ROOT / "hf52-pages"

# This is the full, valid tracker JS from the feature branch. Only its
# network writes and optional geo-fetch are removed; event processing and
# campaign messages remain precisely the branch implementation.
SEND_CODE = (
    "try{fetch(endpoint,{method:'POST',headers:headers,"
    "body:JSON.stringify(payload),keepalive:true,mode:'cors'})"
    ".catch(function(){});}catch(e){}"
)
GEO_CODE = "fetch('/__af_geo',{cache:'no-store',credentials:'same-origin'})"

SAFETY_JS = r"""
<script id="hf52-pages-protections">
(function () {
  'use strict';
  const root=document.createElement('div');
  root.id='hf52-preview-dialog';
  root.hidden=true;
  root.style.cssText='position:fixed;inset:0;z-index:2147483647;background:rgba(5,20,37,.75);display:grid;place-items:center;padding:15px;font:14px system-ui,sans-serif';
  root.innerHTML='<section style="background:white;color:#153854;width:min(95vw,640px);max-height:85vh;overflow:auto;border-radius:15px;padding:18px;box-shadow:0 20px 60px #0006">'+
    '<h2 style="margin:0 0 8px;font-size:19px">Prévia de homologação</h2>'+
    '<p id="hf52-preview-note">Esta é uma simulação. Nenhuma mensagem foi enviada.</p>'+
    '<textarea id="hf52-preview-text" readonly style="box-sizing:border-box;width:100%;min-height:145px;resize:vertical;padding:12px;border:1px solid #8caecb;border-radius:8px;font:13px system-ui,sans-serif"></textarea>'+
    '<div style="display:flex;gap:9px;flex-wrap:wrap;margin-top:12px">'+
    '<button id="hf52-preview-copy" style="background:#1171ae;color:white;border:0;padding:11px 15px;border-radius:9px;cursor:pointer">Copiar texto</button>'+
    '<button id="hf52-preview-close" style="background:#e5f2fd;color:#145482;border:0;padding:11px 15px;border-radius:9px;cursor:pointer">Fechar</button>'+
    '</div></section>';
  root.style.display='none';
  document.body.appendChild(root);
  const messageField=root.querySelector('#hf52-preview-text');
  function show(text,note) {
    messageField.value=text||'';
    root.querySelector('#hf52-preview-note').textContent=note||'Mensagem simulada. Nenhuma mensagem foi enviada.';
    root.hidden=false;root.style.display='grid';
  }
  root.querySelector('#hf52-preview-close').addEventListener('click',()=>{
    root.hidden=true;root.style.display='none';
  });
  root.querySelector('#hf52-preview-copy').addEventListener('click',()=>{
    messageField.select();
    try{document.execCommand('copy');}catch(e){}
  });
  // Intercept only outbound WhatsApp; allow the production HF52 click
  // event handler to update the href before reading the draft in next tick.
  document.addEventListener('click',event=>{
    const a=event.target&&event.target.closest&&event.target.closest('a[href]');
    if(!a)return;
    let u;
    try{u=new URL(a.href,location.href);}catch(e){return;}
    if(u.hostname==='wa.me' || u.hostname==='api.whatsapp.com'){
      event.preventDefault();
      setTimeout(()=>{
        let draft='';
        try{draft=new URL(a.href).searchParams.get('text')||'';}catch(e){}
        show(draft,'Prévia: texto de orçamento preparado. O WhatsApp não foi aberto e nenhuma mensagem foi enviada.');
      },0);
    }else if(a.getAttribute('href')?.startsWith('/')){
      event.preventDefault();
      show('','Esta prévia inclui a vitrine principal. Outras páginas ficam disponíveis no site oficial, não nesta hospedagem de teste.');
    }
  },true);
  // The cart opens WhatsApp via window.open; return a truthy stub to avoid
  // its fallback assigning window.location.href.
  const originalOpen=window.open;
  window.open=function(url,target,features){
    try{
      const u=new URL(url,location.href);
      if(u.hostname==='wa.me' || u.hostname==='api.whatsapp.com'){
        show(u.searchParams.get('text')||'','Prévia do carrinho: o pedido NÃO foi enviado ao WhatsApp.');
        return {closed:false};
      }
    }catch(e){}
    return null; // no external popup from this isolated preview
  };
  window.__HF52_PREVIEW=true;
})();
</script>
"""


def replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    result, count = re.subn(pattern, lambda _: replacement, text, count=1, flags=re.I | re.S)
    if count != 1:
        raise RuntimeError(f"Prévia não pode substituir {label}: {count} ocorrências")
    return result


def build_online_preview() -> Path:
    html_path=build_public_preview()
    page=html_path.read_text(encoding="utf-8")

    # Original live page has a cart already; substitute the actual branch
    # code and stylesheet without duplicating widgets or click listeners.
    match=re.search(
        r'<script\b[^>]*id=["\']afquote-js["\'][^>]*>([\s\S]*?)</script>',
        page, flags=re.I,
    )
    if not match:
        raise RuntimeError("Carrinho original ausente: não publicar prévia parcial")
    config=re.search(r'const CONFIG\s*=\s*(\{[^;\n]+\});',match.group(1))
    if not config:
        raise RuntimeError("Não foi possível ler configuração pública do carrinho")
    phone=json.loads(config.group(1)).get("number","")
    if not re.fullmatch(r'55\d{10,11}',str(phone)):
        raise RuntimeError("WhatsApp público inválido; não publicar prévia")
    script=CART_JS.replace('__CONFIG__',json.dumps({"number":phone}))
    page=replace_once(
        page,
        r'<script\b[^>]*id=["\']afquote-js["\'][^>]*>[\s\S]*?</script>',
        '<script id="afquote-js">'+script+'</script>',
        "JS de carrinho",
    )
    page=replace_once(
        page,
        r'<style\b[^>]*id=["\']afquote-css["\'][^>]*>[\s\S]*?</style>',
        '<style id="afquote-css">'+CART_CSS+'</style>',
        "CSS de carrinho",
    )

    # Instantiate real HF52 tracking code with deliberately fake credentials.
    # All possible API writes are replaced with an IN-MEMORY event collector.
    config={"url":"https://hf52-preview.invalid","key":"sb_publishable_preview_no_network"}
    with patch.object(metrics,"tracking_available",return_value=True),patch.object(
        metrics,"public_config",return_value=config
    ):
        page=metrics.inject_tracking(page)
    if not page.count('id="alphafest-site-metrics"')==1:
        raise RuntimeError("Prévia não tem rastreador HF52 exatamente uma vez")
    if page.count(SEND_CODE)!=1 or page.count(GEO_CODE)!=1:
        raise RuntimeError("Contrato do rastreador mudou: não publicar prévia sem revisão")
    page=page.replace(
        SEND_CODE,
        "try{(window.__HF52_PREVIEW_EVENTS=window.__HF52_PREVIEW_EVENTS||[])"
        ".push(payload);}catch(e){}",
    )
    page=page.replace(
        GEO_CODE,
        "Promise.resolve({ok:true,json:()=>Promise.resolve({})})",
    )
    if "fetch(endpoint" in page or "fetch('/__af_geo'" in page:
        raise RuntimeError("Rastreamento de rede permaneceu na prévia")

    page=page.replace(
        "PRÉVIA ISOLADA HF65.24.52 — NÃO PUBLICADA • SEM RASTREAMENTO REAL",
        "PRÉVIA ONLINE HF65.24.52 — NÃO É O SITE OFICIAL • WHATSAPP SIMULADO",
        1,
    )
    if 'id="hf52-preview-warning"' not in page:
        raise RuntimeError("Aviso persistente da prévia não encontrado")
    header=(
        '<meta name="robots" content="noindex,nofollow,noarchive">'
        '<meta name="referrer" content="no-referrer">'
        '<meta http-equiv="Content-Security-Policy" '
        'content="connect-src &#39;none&#39;; form-action &#39;none&#39;">'
    )
    page=page.replace("</head>",header+"</head>",1)
    page=page.replace("</body>",SAFETY_JS+"</body>",1)

    # Relative product link works both at /alphafest-manager/ and locally.
    help_text=(
        '<p style="padding:7px 12px;margin:4px 0 0;font:12px system-ui,sans-serif;'
        'color:#17466e;background:#eff8ff" id="hf52-preview-info">'
        'Teste a ficha e o carrinho nesta página. Visitas e cliques ficam apenas '
        'na memória deste navegador. WhatsApp bloqueado para evitar contatos reais. '
        'Esta é uma prévia pública de homologação, não uma publicação no Cloudflare.'
        '</p>'
    )
    page=page.replace('id="hf52-preview-warning"', 'id="hf52-preview-warning"',1)
    page=page.replace("</body>",help_text+"</body>",1)

    OUT.mkdir(exist_ok=True)
    out=OUT/"index.html"
    out.write_text(page,encoding="utf-8")
    (OUT/".nojekyll").write_text("",encoding="utf-8")
    (OUT/"robots.txt").write_text("User-agent: *\nDisallow: /\n",encoding="utf-8")
    print(
        f"Prévia para hospedagem separada preparada: {len(page)/1_000_000:.1f} MB "
        "92 produtos, JS de ficha/carrinho/UTM da branch, métricas só em memória",
        flush=True,
    )
    return out


def test_online_preview(output: Path) -> None:
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread
    from playwright.sync_api import sync_playwright
    from urllib.parse import urlencode
    from functools import partial

    server=ThreadingHTTPServer(
        ("127.0.0.1",0),
        partial(SimpleHTTPRequestHandler,directory=str(OUT)),
    )
    worker=Thread(target=server.serve_forever,daemon=True)
    worker.start()
    host=f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            for kind,width,height,mobile in [
                ("desktop",1366,850,False),
                ("celular",390,844,True),
            ]:
                ctx=browser.new_context(
                    viewport={"width":width,"height":height},
                    has_touch=mobile,is_mobile=mobile,
                )
                blocked_post=[]
                def guard(route):
                    req=route.request
                    if req.method!="GET":
                        blocked_post.append(req.url)
                        route.abort()
                    elif req.url.startswith(host+"/"):
                        route.continue_()
                    else:
                        route.abort()
                ctx.route("**/*",guard)
                page=ctx.new_page()
                url=host+"/?"+urlencode({
                    "produto":PRODUCT_SLUG,
                    "utm_source":"instagram",
                    "utm_medium":"stories",
                    "utm_campaign":"hf52-preview-online",
                })
                page.goto(url,wait_until="domcontentloaded",timeout=30000)
                page.wait_for_function("window.__alphafestMetricsReady===true")
                page.locator("#product-detail-modal").wait_for(state="visible")
                assert page.locator("#product-detail-name").inner_text().strip()==PRODUCT_NAME
                assert page.evaluate("window.__HF52_PREVIEW===true")
                assert page.evaluate("(window.__HF52_PREVIEW_EVENTS||[]).length")>=2
                page.locator("#product-detail-whatsapp").click(timeout=5000)
                page.locator("#hf52-preview-dialog").wait_for(state="visible")
                draft=page.locator("#hf52-preview-text").input_value()
                assert "Referência da campanha: instagram/stories/hf52-preview-online" in draft
                page.locator("#hf52-preview-close").click()
                page.locator("#afquote-add").click(timeout=5000)
                page.locator("#afquote-review").click(timeout=5000)
                cart=page.locator("#afquote-message").input_value()
                assert PRODUCT_NAME in cart
                assert "Referência da campanha: instagram/stories/hf52-preview-online" in cart
                page.locator("#afquote-send").click(timeout=5000)
                page.locator("#hf52-preview-dialog").wait_for(state="visible")
                assert "Referência da campanha:" in page.locator("#hf52-preview-text").input_value()
                assert not blocked_post
                events=page.evaluate("window.__HF52_PREVIEW_EVENTS||[]")
                assert any(e["event_type"]=="product_open" for e in events)
                assert sum(e["event_type"]=="whatsapp_click" for e in events)>=2
                print(f"{kind}: prévia validada, ficha e carrinho, WhatsApp simulado e eventos locais",flush=True)
                ctx.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    output=build_online_preview()
    if args.check:
        test_online_preview(output)
