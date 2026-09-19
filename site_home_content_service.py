"""HF65.14 — conteúdo administrável da Home AlphaFest.

Mantém banner informativo, depoimentos, empresas/clientes e CTA principal em
um documento isolado. Não duplica Catálogo/Galeria e não publica sozinho.
"""
from __future__ import annotations

import html
import re
from typing import Any, Dict, List

DEFAULT_HOME_CONTENT_CONFIG: Dict[str, Any] = {
    "hero_cta_text": "Entre para nosso canal",
    "hero_cta_url": "https://whatsapp.com/channel/0029VbDLvQQLI8YOtOO2lG3I",
    "banners": [],
    "testimonials": [],
    "clients": [],
}


def _safe_url(value: Any) -> str:
    url = str(value or "").strip()
    return url if re.match(r"^https?://", url, flags=re.I) else ""


def _clean_image(value: Any) -> str:
    src = str(value or "").strip()
    if src.startswith(("https://", "http://", "data:image/")):
        return src
    return ""


def normalize_home_content_config(value: Any) -> Dict[str, Any]:
    cfg = dict(DEFAULT_HOME_CONTENT_CONFIG)
    if isinstance(value, dict):
        cfg.update({k: v for k, v in value.items() if v is not None})
    cfg["hero_cta_text"] = str(cfg.get("hero_cta_text") or "Entre para nosso canal").strip()[:80]
    cfg["hero_cta_url"] = _safe_url(cfg.get("hero_cta_url")) or DEFAULT_HOME_CONTENT_CONFIG["hero_cta_url"]

    banners: List[Dict[str, Any]] = []
    for i, item in enumerate(cfg.get("banners") or []):
        if not isinstance(item, dict):
            continue
        src = _clean_image(item.get("image_src"))
        if not src:
            continue
        banners.append({
            "id": str(item.get("id") or f"banner-{i+1}")[:80],
            "image_src": src,
            "title": str(item.get("title") or "").strip()[:140],
            "link": _safe_url(item.get("link")),
            "active": bool(item.get("active", True)),
        })
    cfg["banners"] = banners[:12]

    testimonials: List[Dict[str, Any]] = []
    for i, item in enumerate(cfg.get("testimonials") or []):
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        testimonials.append({
            "id": str(item.get("id") or f"testimonial-{i+1}")[:80],
            "name": str(item.get("name") or "Cliente AlphaFest").strip()[:100],
            "company": str(item.get("company") or "").strip()[:120],
            "text": text[:700],
            "active": bool(item.get("active", True)),
        })
    cfg["testimonials"] = testimonials[:30]

    clients: List[Dict[str, Any]] = []
    for i, item in enumerate(cfg.get("clients") or []):
        if not isinstance(item, dict):
            continue
        company = str(item.get("company") or "").strip()
        headline = str(item.get("headline") or "").strip()
        description = str(item.get("description") or "").strip()
        src = _clean_image(item.get("image_src"))
        if not (company or headline or description or src):
            continue
        clients.append({
            "id": str(item.get("id") or f"client-{i+1}")[:80],
            "company": company[:120],
            "headline": headline[:220],
            "description": description[:900],
            "image_src": src,
            "link": _safe_url(item.get("link")),
            "active": bool(item.get("active", True)),
        })
    cfg["clients"] = clients[:24]
    return cfg


def banner_carousel_html(config: Any) -> str:
    cfg = normalize_home_content_config(config)
    items = [x for x in cfg["banners"] if x.get("active")]
    if not items:
        return ""
    slides, dots = [], []
    for i, item in enumerate(items):
        src = html.escape(str(item.get("image_src") or ""), quote=True)
        title = str(item.get("title") or "Banner informativo AlphaFest").strip()
        img = f'<img src="{src}" alt="{html.escape(title, quote=True)}" loading="{("eager" if i == 0 else "lazy")}">'
        link = str(item.get("link") or "").strip()
        if link:
            img = f'<a href="{html.escape(link, quote=True)}" target="_blank" rel="noopener">{img}</a>'
        slides.append(f'<article class="hf6514-banner-slide" data-hf6514-banner-slide="{i}">{img}</article>')
        dots.append(f'<button type="button" class="hf6514-banner-dot{" active" if i == 0 else ""}" data-hf6514-banner-dot="{i}" aria-label="Ir para banner {i+1}"></button>')
    controls = ""
    if len(items) > 1:
        controls = (
            '<button type="button" class="hf6514-banner-arrow prev" aria-label="Banner anterior">‹</button>'
            '<button type="button" class="hf6514-banner-arrow next" aria-label="Próximo banner">›</button>'
            f'<div class="hf6514-banner-dots">{"".join(dots)}</div>'
        )
    return (
        '<section class="hf6514-banner" id="novidades"><div class="hf6514-banner-shell">'
        f'<div class="hf6514-banner-track">{"".join(slides)}</div>{controls}</div></section>'
    )


def testimonials_html(config: Any) -> str:
    cfg = normalize_home_content_config(config)
    items = [x for x in cfg["testimonials"] if x.get("active")]
    if not items:
        return ""
    cards = []
    for item in items:
        company = str(item.get("company") or "").strip()
        meta = f'<span>{html.escape(company)}</span>' if company else ""
        cards.append(
            '<article class="hf6514-testimonial">'
            '<div class="hf6514-stars" aria-label="5 estrelas">★★★★★</div>'
            f'<p>“{html.escape(str(item.get("text") or ""))}”</p>'
            f'<strong>{html.escape(str(item.get("name") or "Cliente AlphaFest"))}</strong>{meta}'
            '</article>'
        )
    return (
        '<section class="hf6514-testimonials" id="depoimentos"><div class="hf48-wrap">'
        '<div class="hf48-section-heading"><div><span class="hf48-kicker">Quem compra, conta</span>'
        '<h2>Depoimentos de clientes</h2><p>Experiências compartilhadas por quem já fez projetos com a AlphaFest.</p></div></div>'
        f'<div class="hf6514-testimonials-track">{"".join(cards)}</div></div></section>'
    )


def client_showcase_html(config: Any) -> str:
    cfg = normalize_home_content_config(config)
    items = [x for x in cfg["clients"] if x.get("active")]
    if not items:
        return ""
    slides, dots = [], []
    for i, item in enumerate(items):
        company = str(item.get("company") or "Cliente AlphaFest").strip()
        headline = str(item.get("headline") or f"Projeto desenvolvido para {company}").strip()
        description = str(item.get("description") or "").strip()
        src = str(item.get("image_src") or "").strip()
        media = (
            f'<div class="hf6514-client-media"><img src="{html.escape(src, quote=True)}" alt="{html.escape(company, quote=True)}" loading="lazy"></div>'
            if src else '<div class="hf6514-client-media hf6514-client-placeholder">AlphaFest</div>'
        )
        link = str(item.get("link") or "").strip()
        more = f'<a href="{html.escape(link, quote=True)}" target="_blank" rel="noopener">Saiba mais →</a>' if link else ""
        slides.append(
            f'<article class="hf6514-client-slide" data-hf6514-client-slide="{i}">{media}'
            f'<div class="hf6514-client-copy"><span>{html.escape(company)}</span><h3>{html.escape(headline)}</h3>'
            f'<p>{html.escape(description)}</p>{more}</div></article>'
        )
        dots.append(f'<button type="button" class="hf6514-client-dot{" active" if i == 0 else ""}" data-hf6514-client-dot="{i}" aria-label="Empresa {i+1}"></button>')
    controls = ""
    if len(items) > 1:
        controls = (
            '<button type="button" class="hf6514-client-arrow prev" aria-label="Empresa anterior">‹</button>'
            '<button type="button" class="hf6514-client-arrow next" aria-label="Próxima empresa">›</button>'
            f'<div class="hf6514-client-dots">{"".join(dots)}</div>'
        )
    return (
        '<section class="hf6514-clients" id="clientes"><div class="hf48-wrap">'
        '<div class="hf48-section-heading"><div><span class="hf48-kicker">Projetos que ganham vida</span>'
        '<h2>Empresas e clientes AlphaFest</h2><p>Alguns projetos, ações e personalizados produzidos para nossos clientes.</p></div></div>'
        f'<div class="hf6514-client-shell"><div class="hf6514-client-track">{"".join(slides)}</div>{controls}</div></div></section>'
    )


HOME_CONTENT_CSS = r'''
.hf6514-banner{background:#fff;padding:24px 24px 10px}.hf6514-banner-shell{position:relative;max-width:1480px;margin:auto;overflow:hidden;border-radius:22px;background:#eef5fb;box-shadow:0 12px 32px rgba(18,35,61,.08);aspect-ratio:10/3}.hf6514-banner-track{display:flex;height:100%;transition:transform .55s cubic-bezier(.2,.75,.25,1)}.hf6514-banner-slide{flex:0 0 100%;height:100%;min-width:0}.hf6514-banner-slide a,.hf6514-banner-slide img{display:block;width:100%;height:100%}.hf6514-banner-slide img{object-fit:cover}.hf6514-banner-arrow,.hf6514-client-arrow{position:absolute;top:50%;transform:translateY(-50%);z-index:4;width:42px;height:42px;border:1px solid rgba(255,255,255,.75);border-radius:50%;background:rgba(255,255,255,.92);color:#0875d4;font-size:28px;cursor:pointer;box-shadow:0 6px 18px rgba(18,35,61,.15)}.hf6514-banner-arrow.prev,.hf6514-client-arrow.prev{left:12px}.hf6514-banner-arrow.next,.hf6514-client-arrow.next{right:12px}.hf6514-banner-dots,.hf6514-client-dots{position:absolute;z-index:5;left:50%;bottom:12px;transform:translateX(-50%);display:flex;gap:7px}.hf6514-banner-dot,.hf6514-client-dot{width:9px;height:9px;border:0;border-radius:999px;background:rgba(255,255,255,.68);padding:0;cursor:pointer;box-shadow:0 0 0 1px rgba(13,63,107,.18)}.hf6514-banner-dot.active,.hf6514-client-dot.active{width:27px;background:#0875d4}
.hf6514-testimonials{padding:64px 24px;background:linear-gradient(135deg,#f5fbff,#fff,#fff3f9)}.hf6514-testimonials-track{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(290px,1fr);gap:14px;overflow-x:auto;scroll-snap-type:x mandatory;padding:2px 2px 14px;scrollbar-width:thin}.hf6514-testimonial{scroll-snap-align:start;border:1px solid #dfeaf5;border-radius:20px;background:#fff;padding:22px;box-shadow:0 8px 24px rgba(18,35,61,.055)}.hf6514-stars{letter-spacing:2px;color:#f4b400;font-size:16px}.hf6514-testimonial p{font-size:15px;line-height:1.65;color:#526a83;min-height:72px}.hf6514-testimonial strong{display:block;color:#173d66}.hf6514-testimonial span{display:block;margin-top:3px;font-size:12px;color:#7a8fa5}
.hf6514-clients{padding:68px 24px;background:#fff}.hf6514-client-shell{position:relative;max-width:1120px;margin:auto;overflow:hidden;border-radius:28px}.hf6514-client-track{display:flex;transition:transform .55s cubic-bezier(.2,.75,.25,1)}.hf6514-client-slide{flex:0 0 100%;min-width:0;display:grid;grid-template-columns:.72fr 1.28fr;gap:0;min-height:350px;background:#0d1320;color:#fff}.hf6514-client-slide:nth-child(even){background:#fff0fa;color:#11233d}.hf6514-client-media{min-height:350px;overflow:hidden;background:#eaf4fb}.hf6514-client-media img{width:100%;height:100%;object-fit:cover;display:block}.hf6514-client-placeholder{display:flex;align-items:center;justify-content:center;font-size:34px;font-weight:950;color:#0875d4}.hf6514-client-copy{padding:48px 56px;display:flex;flex-direction:column;justify-content:center}.hf6514-client-copy>span{font-size:13px;font-weight:950;letter-spacing:.08em;text-transform:uppercase;color:#70c8ff}.hf6514-client-slide:nth-child(even) .hf6514-client-copy>span{color:#0875d4}.hf6514-client-copy h3{font-size:clamp(28px,3.2vw,46px);line-height:1.08;margin:10px 0 16px}.hf6514-client-copy p{font-size:16px;line-height:1.65;opacity:.84;margin:0}.hf6514-client-copy a{margin-top:20px;color:inherit;font-weight:900}.hf6514-client-dots{bottom:15px}.hf6514-client-dot{background:rgba(255,255,255,.52)}
.hf6514-channel-cta{display:inline-flex!important;align-items:center;gap:9px}.hf6514-channel-cta svg{width:20px;height:20px;fill:currentColor}
@media(max-width:900px){.hf6514-banner{padding:16px 14px 6px}.hf6514-banner-shell{border-radius:16px}.hf6514-client-slide{grid-template-columns:1fr}.hf6514-client-media{min-height:260px;max-height:330px}.hf6514-client-copy{padding:30px 28px 54px}.hf6514-client-copy h3{font-size:30px}}
@media(max-width:620px){.hf6514-banner{padding:10px 10px 2px}.hf6514-banner-shell{aspect-ratio:16/7;border-radius:14px}.hf6514-banner-arrow{width:34px;height:34px}.hf6514-banner-arrow.prev{left:6px}.hf6514-banner-arrow.next{right:6px}.hf6514-banner-dots{bottom:7px}.hf6514-testimonials,.hf6514-clients{padding:44px 14px}.hf6514-testimonials-track{grid-auto-columns:86vw}.hf6514-client-shell{border-radius:20px}.hf6514-client-media{min-height:220px}.hf6514-client-copy{padding:24px 20px 52px}.hf6514-client-copy h3{font-size:27px}}
'''

HOME_CONTENT_JS = r'''
(function(){
  function carousel(shellSel,trackSel,slideSel,dotSel,prevSel,nextSel,interval){
    const shell=document.querySelector(shellSel); if(!shell) return;
    const track=shell.querySelector(trackSel), slides=[...shell.querySelectorAll(slideSel)], dots=[...shell.querySelectorAll(dotSel)];
    if(!track||!slides.length) return; let idx=0,timer=null,touch=null;
    function paint(){track.style.transform='translateX(-'+(idx*100)+'%)';dots.forEach((d,i)=>d.classList.toggle('active',i===idx));}
    function go(n){idx=(n+slides.length)%slides.length;paint();}
    function start(){if(timer)clearInterval(timer);if(slides.length>1)timer=setInterval(()=>go(idx+1),interval||5500);}
    const prev=shell.querySelector(prevSel),next=shell.querySelector(nextSel);
    if(prev)prev.addEventListener('click',()=>{go(idx-1);start();});if(next)next.addEventListener('click',()=>{go(idx+1);start();});
    dots.forEach((d,i)=>d.addEventListener('click',()=>{go(i);start();}));
    shell.addEventListener('mouseenter',()=>{if(timer)clearInterval(timer);timer=null;});shell.addEventListener('mouseleave',start);
    shell.addEventListener('touchstart',e=>{touch=e.changedTouches&&e.changedTouches[0]?e.changedTouches[0].clientX:null;},{passive:true});
    shell.addEventListener('touchend',e=>{if(touch===null)return;const end=e.changedTouches&&e.changedTouches[0]?e.changedTouches[0].clientX:touch;const delta=end-touch;touch=null;if(Math.abs(delta)>40){go(idx+(delta<0?1:-1));start();}},{passive:true});
    paint();start();
  }
  carousel('.hf6514-banner-shell','.hf6514-banner-track','.hf6514-banner-slide','.hf6514-banner-dot','.hf6514-banner-arrow.prev','.hf6514-banner-arrow.next',5200);
  carousel('.hf6514-client-shell','.hf6514-client-track','.hf6514-client-slide','.hf6514-client-dot','.hf6514-client-arrow.prev','.hf6514-client-arrow.next',6500);
})();
'''
