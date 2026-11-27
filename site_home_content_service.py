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


def _clean_video(value: Any) -> str:
    src = str(value or "").strip()
    if src.startswith(("https://", "http://", "data:video/")):
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
        kind = str(item.get("kind") or "text").strip().lower()
        if kind not in {"text", "image", "video"}:
            kind = "text"
        text_value = str(item.get("text") or "").strip()
        image_src = _clean_image(item.get("image_src"))
        video_src = _clean_video(item.get("video_src") or item.get("media_src"))
        if kind == "text" and not text_value:
            continue
        if kind == "image" and not image_src:
            continue
        if kind == "video" and not video_src:
            continue
        testimonials.append({
            "id": str(item.get("id") or f"testimonial-{i+1}")[:80],
            "kind": kind,
            "name": str(item.get("name") or "Cliente AlphaFest").strip()[:100],
            "company": str(item.get("company") or "").strip()[:120],
            "text": text_value[:700],
            "image_src": image_src,
            "video_src": video_src,
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
    """Galeria de imagens originais, sem duplicar textos dos cards.

    Os textos e nomes cadastrados são mantidos no documento de origem, e os
    depoimentos textuais/vídeos continuam exibidos. Só muda a apresentação
    pública dos cards com imagem; nada é alterado ou gravado no Manager.
    """
    cfg = normalize_home_content_config(config)
    items = [x for x in cfg["testimonials"] if x.get("active")]
    if not items:
        return ""
    cards = []
    imagens = 0
    for index, item in enumerate(items, 1):
        kind = str(item.get("kind") or "text").strip().lower()
        nome = str(item.get("name") or "Cliente AlphaFest").strip()
        company = str(item.get("company") or "").strip()
        text_value = str(item.get("text") or "").strip()

        if kind == "image":
            # Não duplicar o texto da arte nem o src (pode conter data:image
            # em base64). O zoom lê o src da imagem existente no DOM.
            imagens += 1
            src = html.escape(str(item.get("image_src") or ""), quote=True)
            alt = html.escape(f"Depoimento em imagem de {nome}", quote=True)
            cards.append(
                '<article class="hf6514-testimonial hf6514-testimonial-image">'
                f'<button type="button" class="hf6514-testimonial-zoom" '
                f'aria-label="Ampliar imagem do depoimento {index}">'
                f'<img src="{src}" alt="{alt}" loading="lazy" decoding="async">'
                '</button></article>'
            )
            continue

        meta = f'<span>{html.escape(company)}</span>' if company else ""
        corpo = f'<p>“{html.escape(text_value)}”</p>' if text_value else ""
        if kind == "video":
            video_src = html.escape(str(item.get("video_src") or ""), quote=True)
            media = (
                '<div class="hf6514-testimonial-media">'
                '<video controls preload="metadata" playsinline aria-label="Depoimento em vídeo">'
                f'<source src="{video_src}"></video></div>'
            )
            tipo = "Depoimento em vídeo"
        else:
            media = ""
            tipo = "Depoimento por escrito"
        cards.append(
            '<article class="hf6514-testimonial hf6514-testimonial-textual">'
            f'<div class="hf6514-testimonial-kind">{tipo}</div>'
            f'{media}{corpo}<strong>{html.escape(nome)}</strong>{meta}'
            '</article>'
        )

    ampliacao = ""
    if imagens:
        ampliacao = (
            '<dialog class="hf6514-testimonial-dialog" aria-label="Imagem de depoimento ampliada">'
            '<div class="hf6514-testimonial-dialog-body">'
            '<button type="button" class="hf6514-testimonial-close" aria-label="Fechar imagem ampliada">×</button>'
            '<img class="hf6514-testimonial-full" alt="">'
            '</div></dialog>'
        )
    return (
        '<section class="hf6514-testimonials" id="depoimentos"><div class="hf48-wrap">'
        '<div class="hf48-section-heading"><div><span class="hf48-kicker">Quem compra, conta</span>'
        '<h2>O carinho dos nossos clientes 💙</h2>'
        '<p>Cada mensagem que recebemos é uma alegria e nos inspira a continuar criando '
        'momentos especiais. Obrigado pela confiança e pelo carinho com a AlphaFest!</p>'
        '</div></div>'
        f'<div class="hf6514-testimonials-track">{"".join(cards)}</div>'
        f'{ampliacao}</div></section>'
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
.hf6514-testimonials{padding:54px 24px;background:linear-gradient(135deg,#f5fbff,#fff,#fff3f9)}
.hf6514-testimonials .hf48-section-heading{margin-bottom:22px}
.hf6514-testimonials .hf48-section-heading p{max-width:780px;line-height:1.65}
.hf6514-testimonials-track{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));align-items:start;gap:16px;padding:3px 4px 16px;max-width:100%;min-width:0}
.hf6514-testimonial{box-sizing:border-box;min-width:0;border:1px solid #dfeaf5;border-radius:18px;background:#fff;padding:17px;box-shadow:0 8px 24px rgba(18,35,61,.055)}
.hf6514-testimonial-image{padding:9px}
.hf6514-testimonial-zoom{display:block;width:100%;padding:0;border:0;border-radius:12px;overflow:hidden;background:#f5f9fd;cursor:zoom-in}
.hf6514-testimonial-zoom img{display:block;width:100%;aspect-ratio:4/5;object-fit:contain;background:#f5f9fd}
.hf6514-testimonial-zoom:focus-visible,.hf6514-testimonial-close:focus-visible{outline:3px solid #0875d4;outline-offset:3px}
.hf6514-testimonial-kind{display:inline-flex;align-items:center;min-height:24px;padding:4px 10px;border-radius:999px;background:#eaf4ff;color:#0875d4;font-size:11px;font-weight:900;letter-spacing:.03em;text-transform:uppercase;margin-bottom:10px}
.hf6514-testimonial-media{margin:10px 0 14px;border-radius:16px;overflow:hidden;background:#eef5fb;border:1px solid #dce8f4}
.hf6514-testimonial-media video{display:block;width:100%;height:auto;max-height:450px;object-fit:contain;background:#000}
.hf6514-testimonial-textual p{font-size:15px;line-height:1.6;color:#526a83;overflow-wrap:anywhere;margin:10px 0 14px}
.hf6514-testimonial-textual strong{display:block;color:#173d66}
.hf6514-testimonial-textual span{display:block;margin-top:3px;font-size:12px;color:#7a8fa5}
.hf6514-testimonial-dialog{max-width:min(1100px,94vw);max-height:94vh;box-sizing:border-box;margin:auto;padding:15px;border:1px solid #dce8f4;border-radius:16px;background:#fff;box-shadow:0 24px 70px rgba(8,30,64,.34);overflow:auto}
.hf6514-testimonial-dialog::backdrop{background:rgba(10,28,49,.85)}
.hf6514-testimonial-dialog-body{position:relative;padding-top:42px}
.hf6514-testimonial-full{display:block;max-width:100%;max-height:calc(92vh - 85px);width:auto;height:auto;margin:auto;object-fit:contain}
.hf6514-testimonial-close{position:absolute;right:0;top:0;display:grid;place-items:center;width:36px;height:36px;padding:0;background:#eaf4ff;color:#173d66;border:1px solid #cfe0f3;border-radius:50%;font-size:28px;line-height:1;cursor:pointer}

.hf6514-clients{padding:68px 24px;background:#fff}.hf6514-client-shell{position:relative;max-width:1120px;margin:auto;overflow:hidden;border-radius:28px}.hf6514-client-track{display:flex;transition:transform .55s cubic-bezier(.2,.75,.25,1)}.hf6514-client-slide{flex:0 0 100%;min-width:0;display:grid;grid-template-columns:.72fr 1.28fr;gap:0;min-height:350px;background:#0d1320;color:#fff}.hf6514-client-slide:nth-child(even){background:#fff0fa;color:#11233d}.hf6514-client-media{min-height:350px;overflow:hidden;background:#eaf4fb}.hf6514-client-media img{width:100%;height:100%;object-fit:cover;display:block}.hf6514-client-placeholder{display:flex;align-items:center;justify-content:center;font-size:34px;font-weight:950;color:#0875d4}.hf6514-client-copy{padding:48px 56px;display:flex;flex-direction:column;justify-content:center}.hf6514-client-copy>span{font-size:13px;font-weight:950;letter-spacing:.08em;text-transform:uppercase;color:#70c8ff}.hf6514-client-slide:nth-child(even) .hf6514-client-copy>span{color:#0875d4}.hf6514-client-copy h3{font-size:clamp(28px,3.2vw,46px);line-height:1.08;margin:10px 0 16px}.hf6514-client-copy p{font-size:16px;line-height:1.65;opacity:.84;margin:0}.hf6514-client-copy a{margin-top:20px;color:inherit;font-weight:900}.hf6514-client-dots{bottom:15px}.hf6514-client-dot{background:rgba(255,255,255,.52)}
.hf6514-channel-cta{display:inline-flex!important;align-items:center;gap:9px}.hf6514-channel-cta svg{width:20px;height:20px;fill:currentColor}
@media(max-width:900px){.hf6514-testimonials-track{grid-template-columns:repeat(2,minmax(0,1fr))}.hf6514-banner{padding:16px 14px 6px}.hf6514-banner-shell{border-radius:16px}.hf6514-client-slide{grid-template-columns:1fr}.hf6514-client-media{min-height:260px;max-height:330px}.hf6514-client-copy{padding:30px 28px 54px}.hf6514-client-copy h3{font-size:30px}}
@media(max-width:620px){.hf6514-banner{padding:10px 10px 2px}.hf6514-banner-shell{aspect-ratio:16/7;border-radius:14px}.hf6514-banner-arrow{width:34px;height:34px}.hf6514-banner-arrow.prev{left:6px}.hf6514-banner-arrow.next{right:6px}.hf6514-banner-dots{bottom:7px}.hf6514-testimonials,.hf6514-clients{padding:44px 14px}.hf6514-testimonials-track{grid-template-columns:minmax(0,1fr);gap:14px;padding-inline:0}.hf6514-testimonials .hf48-section-heading{margin-bottom:18px}.hf6514-client-shell{border-radius:20px}.hf6514-client-media{min-height:220px}.hf6514-client-copy{padding:24px 20px 52px}.hf6514-client-copy h3{font-size:27px}}
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
  // Zoom acessível: não duplica URLs ou dados base64 de depoimentos na página.
  const galeria=document.querySelector('#depoimentos');
  const modal=galeria&&galeria.querySelector('.hf6514-testimonial-dialog');
  const ampliada=modal&&modal.querySelector('.hf6514-testimonial-full');
  if(galeria&&modal&&ampliada){
    let focoAnterior=null;
    const fechar=()=>{
      if(typeof modal.close==='function') modal.close();
      else {modal.removeAttribute('open');ampliada.removeAttribute('src');if(focoAnterior)focoAnterior.focus();}
    };
    galeria.addEventListener('click',event=>{
      const gatilho=event.target.closest('.hf6514-testimonial-zoom');
      if(!gatilho||!galeria.contains(gatilho))return;
      const imagem=gatilho.querySelector('img');
      if(!imagem)return;
      focoAnterior=gatilho;
      ampliada.src=imagem.currentSrc||imagem.src;
      ampliada.alt=imagem.alt||'Depoimento ampliado';
      if(typeof modal.showModal==='function')modal.showModal();
      else modal.setAttribute('open','');
    });
    const fecharBotao=modal.querySelector('.hf6514-testimonial-close');
    if(fecharBotao)fecharBotao.addEventListener('click',fechar);
    modal.addEventListener('click',event=>{if(event.target===modal)fechar();});
    modal.addEventListener('close',()=>{ampliada.removeAttribute('src');if(focoAnterior)focoAnterior.focus();focoAnterior=null;});
    document.addEventListener('keydown',event=>{
      if(event.key==='Escape'&&modal.hasAttribute('open')&&typeof modal.showModal!=='function')fechar();
    });
  }
})();
'''
