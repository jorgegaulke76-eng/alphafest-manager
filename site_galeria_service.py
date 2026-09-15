"""Galeria pública de trabalhos AlphaFest — HF58 múltiplas categorias.

Somente leitura. A Fonte Única continua sendo ``galeria_trabalhos_db``: entram
na prévia apenas trabalhos não arquivados, explicitamente autorizados e
pré-selecionados para o site no Manager. Este módulo não publica, não persiste
e não torna o bucket privado público.
"""
from __future__ import annotations

import html
import re
import unicodedata
from typing import Any, Callable, Dict, Iterable, List, Optional
from urllib.parse import quote


ImagemResolver = Optional[Callable[[str], str]]


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _slug(valor: Any) -> str:
    base = unicodedata.normalize("NFKD", _texto(valor))
    base = "".join(c for c in base if not unicodedata.combining(c))
    base = re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()
    return base or "sem-informacao"


def _categorias_extras(item: Dict[str, Any], principal: str = "") -> List[str]:
    """HF58: normaliza categorias adicionais sem duplicar a categoria principal."""
    bruto = (item or {}).get("categorias_extras") or []
    if isinstance(bruto, str):
        bruto = [bruto]
    if not isinstance(bruto, (list, tuple, set)):
        bruto = []
    principal_cf = _texto(principal).casefold()
    vistos = set()
    saida: List[str] = []
    for valor in bruto:
        categoria = _texto(valor)
        chave = categoria.casefold()
        if not categoria or chave == principal_cf or chave in vistos:
            continue
        vistos.add(chave)
        saida.append(categoria)
    return saida


def _todas_categorias(item: Dict[str, Any]) -> List[str]:
    principal = _texto((item or {}).get("categoria")) or "Sem categoria"
    return [principal] + _categorias_extras(item, principal)


def _numero_whatsapp(empresa: Dict[str, Any]) -> str:
    numero = re.sub(r"\D", "", _texto((empresa or {}).get("whatsapp_catalogo") or (empresa or {}).get("celular")))
    if numero and not numero.startswith("55"):
        numero = "55" + numero
    return numero


def selecionar_trabalhos_site(galeria: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Retorna somente o que foi liberado manualmente para futura exposição."""
    saida: List[Dict[str, Any]] = []
    for item in galeria or []:
        if not isinstance(item, dict):
            continue
        if bool(item.get("arquivado")):
            continue
        if not bool(item.get("autorizado_publicacao")):
            continue
        if not bool(item.get("selecionado_site")):
            continue
        fotos = [_texto(x) for x in (item.get("fotos") or []) if _texto(x)]
        if not fotos:
            continue
        normalizado = dict(item)
        normalizado["fotos"] = fotos
        normalizado["produto"] = _texto(item.get("produto")) or "Trabalho personalizado"
        normalizado["categoria"] = _texto(item.get("categoria")) or "Sem categoria"
        normalizado["categorias_extras"] = _categorias_extras(item, normalizado["categoria"])
        normalizado["subcategoria"] = _texto(item.get("subcategoria")) or "Sem subcategoria"
        normalizado["tema"] = _texto(item.get("tema"))
        normalizado["cor"] = _texto(item.get("cor"))
        normalizado["ocasiao"] = _texto(item.get("ocasiao"))
        saida.append(normalizado)
    # Os trabalhos mais novos aparecem primeiro, sem depender de um formato de data específico.
    return list(reversed(saida))


def resumir_galeria_site(galeria: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    trabalhos = selecionar_trabalhos_site(galeria)
    categorias = sorted(
        {categoria for trabalho in trabalhos for categoria in _todas_categorias(trabalho) if categoria},
        key=str.casefold,
    )
    subcategorias = sorted({_texto(x.get("subcategoria")) for x in trabalhos if _texto(x.get("subcategoria"))}, key=str.casefold)
    temas = sorted({_texto(x.get("tema")) for x in trabalhos if _texto(x.get("tema"))}, key=str.casefold)
    return {
        "trabalhos": trabalhos,
        "total_trabalhos": len(trabalhos),
        "total_fotos": sum(len(x.get("fotos") or []) for x in trabalhos),
        "categorias": categorias,
        "total_categorias": len(categorias),
        "subcategorias": subcategorias,
        "total_subcategorias": len(subcategorias),
        "temas": temas,
        "total_temas": len(temas),
    }


def gerar_fragmento_galeria(
    galeria: Iterable[Dict[str, Any]],
    empresa: Dict[str, Any],
    *,
    imagem_resolver: ImagemResolver = None,
    limite_fotos: Optional[int] = 24,
) -> Dict[str, Any]:
    """Monta seção, CSS e JS autônomos para a prévia da Galeria.

    ``limite_fotos`` protege a prévia interna quando as imagens privadas são
    embutidas como data URI. A Fonte Única e a quantidade real permanecem
    intactas; o limite só afeta o que é renderizado nesta prévia.
    """
    resumo = resumir_galeria_site(galeria)
    trabalhos = resumo["trabalhos"]
    numero = _numero_whatsapp(empresa)

    categorias = resumo["categorias"]
    options_categoria = ['<option value="todos">Todas as categorias</option>'] + [
        f'<option value="{html.escape(_slug(cat), quote=True)}">{html.escape(cat)}</option>' for cat in categorias
    ]

    # As opções de subcategoria carregam o pai para o filtro em cascata.
    pares_sub = sorted(
        {
            (_texto(t.get("categoria")) or "Sem categoria", _texto(t.get("subcategoria")) or "Sem subcategoria")
            for t in trabalhos
        },
        key=lambda x: (x[0].casefold(), x[1].casefold()),
    )
    options_sub = ['<option value="todos">Todas as subcategorias</option>']
    for categoria, sub in pares_sub:
        options_sub.append(
            f'<option value="{html.escape(_slug(sub), quote=True)}" data-parent="{html.escape(_slug(categoria), quote=True)}">{html.escape(sub)}</option>'
        )

    temas = resumo["temas"]
    options_tema = ['<option value="todos">Todos os temas</option>'] + [
        f'<option value="{html.escape(_slug(tema), quote=True)}">{html.escape(tema)}</option>' for tema in temas
    ]

    cards: List[str] = []
    total_renderizado = 0
    limite = None if limite_fotos is None else max(1, int(limite_fotos))
    for trabalho_indice, trabalho in enumerate(trabalhos):
        trabalho_grupo = _slug(trabalho.get("id") or f"trabalho-{trabalho_indice + 1}")
        produto = _texto(trabalho.get("produto")) or "Trabalho personalizado"
        categoria = _texto(trabalho.get("categoria")) or "Sem categoria"
        categorias_trabalho = _todas_categorias(trabalho)
        categorias_slugs = "|".join(_slug(cat) for cat in categorias_trabalho)
        categorias_extras = _categorias_extras(trabalho, categoria)
        subcategoria = _texto(trabalho.get("subcategoria")) or "Sem subcategoria"
        tema = _texto(trabalho.get("tema"))
        cor = _texto(trabalho.get("cor"))
        ocasiao = _texto(trabalho.get("ocasiao"))
        detalhes = [x for x in [tema, cor, ocasiao] if x]
        detalhe_html = " • ".join(html.escape(x) for x in detalhes)
        mensagem = f"Olá! Vi este trabalho na Galeria da AlphaFest e quero este modelo: {produto}."
        if tema:
            mensagem += f" Tema: {tema}."
        if ocasiao:
            mensagem += f" Ocasião: {ocasiao}."
        mensagem += " Quero definir os detalhes, quantidade e prazo."
        href = f"https://wa.me/{numero}?text={quote(mensagem)}" if numero else "#"
        busca = " ".join([produto, categoria, *categorias_extras, subcategoria, tema, cor, ocasiao])
        busca = unicodedata.normalize("NFKD", busca).encode("ascii", "ignore").decode("ascii").casefold()

        for foto in trabalho.get("fotos") or []:
            if limite is not None and total_renderizado >= limite:
                break
            src = ""
            if imagem_resolver is not None:
                try:
                    src = _texto(imagem_resolver(_texto(foto)))
                except Exception:
                    src = ""
            elif _texto(foto).startswith(("http://", "https://", "data:image/")):
                src = _texto(foto)
            if src:
                imagem = (
                    f'<button type="button" class="gallery-photo gallery-photo-open" '
                    f'data-gallery-group="{html.escape(trabalho_grupo, quote=True)}" '
                    f'data-gallery-title="{html.escape(produto, quote=True)}" '
                    f'aria-label="Ampliar foto de {html.escape(produto, quote=True)}">'
                    f'<img src="{html.escape(src, quote=True)}" alt="{html.escape(produto, quote=True)}" loading="lazy" decoding="async">'
                    '<span class="gallery-photo-zoom" aria-hidden="true">🔍</span></button>'
                )
            else:
                imagem = '<div class="gallery-photo"><div class="gallery-placeholder">AlphaFest</div></div>'
            tema_slug = _slug(tema) if tema else "sem-tema"
            cards.append(
                f'''<article class="gallery-card" data-cat="{html.escape(_slug(categoria), quote=True)}" data-cats="{html.escape(categorias_slugs, quote=True)}" data-sub="{html.escape(_slug(subcategoria), quote=True)}" data-theme="{html.escape(tema_slug, quote=True)}" data-product="{html.escape(_slug(produto), quote=True)}" data-search="{html.escape(busca, quote=True)}">
                {imagem}
                <div class="gallery-body"><div class="gallery-tax">{html.escape(categoria)} <span>›</span> {html.escape(subcategoria)}</div>
                <h3>{html.escape(produto)}</h3>{f'<p>{detalhe_html}</p>' if detalhe_html else '<p>Personalizado produzido pela AlphaFest.</p>'}
                <a class="gallery-cta" href="{html.escape(href, quote=True)}" target="_blank" rel="noopener">💬 Quero este</a></div></article>'''
            )
            total_renderizado += 1
        if limite is not None and total_renderizado >= limite:
            break

    restante = max(0, int(resumo["total_fotos"]) - total_renderizado)
    aviso_limite = (
        f'<div class="gallery-preview-note">Prévia interna mostrando {total_renderizado} de {resumo["total_fotos"]} foto(s) selecionadas. O acervo original não foi alterado.</div>'
        if restante else ""
    )
    vazio = '<div class="gallery-empty">A Galeria está pronta. Assim que um trabalho autorizado for pré-selecionado no Manager, ele aparecerá aqui.</div>'
    secao = f'''<section class="site-section gallery-section" id="galeria"><div class="site-wrap">
      <div class="section-kicker">Galeria AlphaFest</div><h2 class="section-title">Trabalhos realizados para inspirar sua próxima ideia.</h2>
      <p class="section-copy">Veja projetos reais produzidos pela AlphaFest e use os filtros para encontrar referências por categoria, subcategoria e tema.</p>
      <div class="gallery-product-focus" id="gallery-product-focus" hidden><div><span>Trabalhos ligados ao produto</span><strong id="gallery-product-focus-label">Produto</strong></div><button type="button" id="gallery-product-focus-clear">Ver toda a Galeria</button></div>
      <div class="gallery-toolbar" aria-label="Filtros da galeria">
        <label><span>Categoria</span><select id="gallery-cat">{''.join(options_categoria)}</select></label>
        <label><span>Subcategoria</span><select id="gallery-sub">{''.join(options_sub)}</select></label>
        <label><span>Tema</span><select id="gallery-theme">{''.join(options_tema)}</select></label>
        <div class="gallery-count" id="gallery-count">{total_renderizado} foto(s)</div>
      </div>
      <div class="gallery-grid" id="gallery-grid">{''.join(cards) if cards else vazio}</div>{aviso_limite}
    </div>
    <div class="gallery-lightbox" id="gallery-lightbox" hidden aria-hidden="true">
      <div class="gallery-lightbox-backdrop" id="gallery-lightbox-backdrop" aria-hidden="true"></div>
      <div class="gallery-lightbox-panel" role="dialog" aria-modal="true" aria-label="Visualização ampliada da foto">
        <button type="button" class="gallery-lightbox-close" id="gallery-lightbox-close" aria-label="Fechar foto ampliada">×</button>
        <button type="button" class="gallery-lightbox-nav gallery-lightbox-prev" id="gallery-lightbox-prev" aria-label="Foto anterior">‹</button>
        <figure class="gallery-lightbox-figure">
          <img id="gallery-lightbox-image" alt="">
          <figcaption id="gallery-lightbox-caption"></figcaption>
        </figure>
        <button type="button" class="gallery-lightbox-nav gallery-lightbox-next" id="gallery-lightbox-next" aria-label="Próxima foto">›</button>
      </div>
    </div>
    </section>'''

    css = r'''
.gallery-section{background:linear-gradient(180deg,#fff8fc,#ffffff)}
.gallery-product-focus{display:flex;align-items:center;justify-content:space-between;gap:14px;margin:22px 0 -10px;padding:13px 15px;border:1px solid #b9dcf8;border-radius:15px;background:linear-gradient(90deg,#eef8ff,#fff)}.gallery-product-focus[hidden]{display:none}.gallery-product-focus span{display:block;font-size:10px;text-transform:uppercase;letter-spacing:.07em;font-weight:900;color:#6c85a0}.gallery-product-focus strong{display:block;margin-top:2px;color:#153a60}.gallery-product-focus button{border:1px solid #b9d8f0;background:#fff;color:#0b68b5;border-radius:10px;padding:9px 12px;font-weight:900;cursor:pointer}
.gallery-toolbar{display:grid;grid-template-columns:1fr 1fr 1fr auto;gap:12px;align-items:end;margin:26px 0 22px;padding:16px;border:1px solid var(--line);border-radius:18px;background:#fff;box-shadow:0 8px 26px rgba(20,37,61,.04)}
.gallery-toolbar label span{display:block;font-size:11px;font-weight:900;letter-spacing:.05em;text-transform:uppercase;color:#617791;margin:0 0 6px}.gallery-toolbar select{width:100%;border:1px solid #cfe0ee;border-radius:11px;background:#fff;color:var(--ink);padding:11px 12px;font-size:14px;font-weight:750;outline:none}.gallery-count{min-width:105px;text-align:center;padding:12px 13px;border-radius:11px;background:#eef7ff;color:var(--blue);font-weight:900;font-size:13px}
.gallery-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.gallery-card{border:1px solid var(--line);border-radius:18px;overflow:hidden;background:#fff;box-shadow:0 10px 28px rgba(20,37,61,.06);display:flex;flex-direction:column}.gallery-photo{position:relative;width:100%;aspect-ratio:4/3;border:0;padding:0;background:var(--soft);overflow:hidden;display:block}.gallery-photo-open{cursor:zoom-in}.gallery-photo img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .18s ease}.gallery-photo-open:focus-visible{outline:3px solid #1ba7e8;outline-offset:-3px}.gallery-photo-zoom{position:absolute;right:10px;top:10px;width:34px;height:34px;border-radius:999px;display:flex;align-items:center;justify-content:center;background:rgba(4,28,49,.74);color:#fff;font-size:16px;box-shadow:0 5px 16px rgba(0,0,0,.18);pointer-events:none}.gallery-placeholder{height:100%;display:flex;align-items:center;justify-content:center;color:#84a9ca;font-size:24px;font-weight:950}.gallery-body{padding:15px;display:flex;flex-direction:column;flex:1}.gallery-tax{font-size:10px;text-transform:uppercase;letter-spacing:.06em;font-weight:900;color:var(--blue)}.gallery-tax span{color:#92a6b8}.gallery-body h3{font-size:18px;line-height:1.18;margin:7px 0 7px}.gallery-body p{font-size:13px;line-height:1.45;color:#647991;margin:0 0 14px;flex:1}.gallery-cta{display:flex;justify-content:center;align-items:center;min-height:42px;border-radius:10px;background:var(--green);color:#fff;text-decoration:none;font-size:13px;font-weight:900}.gallery-empty{grid-column:1/-1;border:1px dashed #cbddea;border-radius:16px;padding:42px;text-align:center;color:#637993;background:#fff}.gallery-preview-note{margin-top:14px;color:#73869b;font-size:11px;text-align:center}
body.gallery-lightbox-open{overflow:hidden}.gallery-lightbox{position:fixed;inset:0;z-index:10000;display:flex;align-items:center;justify-content:center;padding:24px}.gallery-lightbox[hidden]{display:none}.gallery-lightbox-backdrop{position:absolute;inset:0;background:rgba(2,13,24,.91);backdrop-filter:blur(3px)}.gallery-lightbox-panel{position:relative;z-index:1;width:min(1180px,calc(100% - 24px));max-height:calc(100vh - 32px);display:grid;grid-template-columns:58px minmax(0,1fr) 58px;align-items:center;gap:12px}.gallery-lightbox-figure{margin:0;min-width:0;display:flex;flex-direction:column;align-items:center;justify-content:center}.gallery-lightbox-figure img{display:block;max-width:100%;max-height:calc(100vh - 112px);width:auto;height:auto;object-fit:contain;border-radius:12px;box-shadow:0 20px 60px rgba(0,0,0,.38);background:#fff}.gallery-lightbox-figure figcaption{min-height:24px;margin-top:10px;color:#fff;font-size:13px;font-weight:800;text-align:center;text-shadow:0 1px 2px rgba(0,0,0,.3)}.gallery-lightbox-close,.gallery-lightbox-nav{border:0;color:#fff;background:rgba(255,255,255,.16);backdrop-filter:blur(5px);cursor:pointer;display:flex;align-items:center;justify-content:center}.gallery-lightbox-close{position:absolute;right:0;top:0;transform:translateY(-54px);width:44px;height:44px;border-radius:999px;font-size:31px;line-height:1}.gallery-lightbox-nav{width:52px;height:64px;border-radius:14px;font-size:42px;line-height:1}.gallery-lightbox-nav[hidden]{visibility:hidden}.gallery-lightbox-close:hover,.gallery-lightbox-nav:hover{background:rgba(255,255,255,.28)}.gallery-lightbox-close:focus-visible,.gallery-lightbox-nav:focus-visible{outline:3px solid #fff;outline-offset:3px}
@media(hover:hover) and (pointer:fine){.gallery-photo-open:hover img{transform:scale(1.025)}}
@media(max-width:900px){.gallery-toolbar{grid-template-columns:1fr 1fr}.gallery-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.gallery-count{align-self:stretch;display:flex;align-items:center;justify-content:center}}
@media(max-width:620px){.gallery-product-focus{align-items:stretch;flex-direction:column}.gallery-product-focus button{width:100%;min-height:42px}.gallery-toolbar{grid-template-columns:1fr;padding:13px}.gallery-toolbar select{font-size:16px;min-height:46px}.gallery-count{min-height:44px}.gallery-grid{grid-template-columns:1fr;gap:15px}.gallery-card{border-radius:16px}.gallery-body{padding:14px}.gallery-body h3{font-size:18px}.gallery-cta{min-height:46px}.gallery-photo-zoom{width:38px;height:38px;right:9px;top:9px}.gallery-lightbox{padding:8px}.gallery-lightbox-panel{width:100%;max-height:calc(100vh - 16px);display:block}.gallery-lightbox-figure img{max-width:100%;max-height:calc(100vh - 86px);border-radius:8px}.gallery-lightbox-figure figcaption{font-size:12px;margin:8px 52px 0;min-height:18px}.gallery-lightbox-close{right:8px;top:8px;transform:none;width:46px;height:46px;z-index:2;background:rgba(0,0,0,.52)}.gallery-lightbox-nav{position:absolute;top:50%;transform:translateY(-50%);width:46px;height:58px;z-index:2;background:rgba(0,0,0,.48)}.gallery-lightbox-prev{left:6px}.gallery-lightbox-next{right:6px}}
'''

    # O JS é isolado por IDs/classes gallery-* para não interferir nos filtros de Produtos.
    js = r'''
(function(){
 const cat=document.getElementById('gallery-cat'),sub=document.getElementById('gallery-sub'),theme=document.getElementById('gallery-theme'),count=document.getElementById('gallery-count');
 if(!cat||!sub||!theme||!count)return;
 const cards=[...document.querySelectorAll('.gallery-card')], subOptions=[...sub.options], themeOptions=[...theme.options];
 const focus=document.getElementById('gallery-product-focus'),focusLabel=document.getElementById('gallery-product-focus-label'),focusClear=document.getElementById('gallery-product-focus-clear');
 const lightbox=document.getElementById('gallery-lightbox'),lightboxBackdrop=document.getElementById('gallery-lightbox-backdrop'),lightboxClose=document.getElementById('gallery-lightbox-close'),lightboxPrev=document.getElementById('gallery-lightbox-prev'),lightboxNext=document.getElementById('gallery-lightbox-next'),lightboxImage=document.getElementById('gallery-lightbox-image'),lightboxCaption=document.getElementById('gallery-lightbox-caption');
 const photoButtons=[...document.querySelectorAll('.gallery-photo-open')];
 let productFocus='',lightboxItems=[],lightboxIndex=0,lightboxTrigger=null;
 function renderLightbox(){if(!lightboxItems.length||!lightboxImage)return;const btn=lightboxItems[lightboxIndex],img=btn?btn.querySelector('img'):null;if(!btn||!img)return;lightboxImage.src=img.currentSrc||img.src;lightboxImage.alt=img.alt||'Foto ampliada da Galeria AlphaFest';const titulo=btn.dataset.galleryTitle||img.alt||'Galeria AlphaFest';if(lightboxCaption)lightboxCaption.textContent=lightboxItems.length>1?titulo+' · '+(lightboxIndex+1)+' de '+lightboxItems.length:titulo;const multi=lightboxItems.length>1;if(lightboxPrev)lightboxPrev.hidden=!multi;if(lightboxNext)lightboxNext.hidden=!multi;}
 function openLightbox(btn){if(!lightbox||!btn)return;const group=btn.dataset.galleryGroup||'';lightboxItems=photoButtons.filter(x=>x.dataset.galleryGroup===group&&x.querySelector('img'));lightboxIndex=Math.max(0,lightboxItems.indexOf(btn));lightboxTrigger=btn;renderLightbox();lightbox.hidden=false;lightbox.setAttribute('aria-hidden','false');document.body.classList.add('gallery-lightbox-open');requestAnimationFrame(()=>{if(lightboxClose)lightboxClose.focus({preventScroll:true});});}
 function closeLightbox(){if(!lightbox||lightbox.hidden)return;lightbox.hidden=true;lightbox.setAttribute('aria-hidden','true');document.body.classList.remove('gallery-lightbox-open');if(lightboxTrigger&&typeof lightboxTrigger.focus==='function'){try{lightboxTrigger.focus({preventScroll:true});}catch(e){lightboxTrigger.focus();}}}
 function moveLightbox(step){if(lightboxItems.length<2)return;lightboxIndex=(lightboxIndex+step+lightboxItems.length)%lightboxItems.length;renderLightbox();}
 function clearProductFocus(){productFocus='';if(focus)focus.hidden=true;}
 function cardHasCat(card,c){if(c==='todos')return true;const raw=card.dataset.cats||card.dataset.cat||'';return raw.split('|').filter(Boolean).includes(c);}
 function refreshSub(){const c=cat.value;subOptions.forEach((o,i)=>{if(i===0){o.hidden=false;return;}o.hidden=(c!=='todos'&&o.dataset.parent!==c);});if(sub.selectedOptions[0]&&sub.selectedOptions[0].hidden)sub.value='todos';}
 function refreshTheme(){const c=cat.value,s=sub.value,allowed=new Set();cards.forEach(x=>{if(cardHasCat(x,c)&&(s==='todos'||x.dataset.sub===s)&&(!productFocus||x.dataset.product===productFocus))allowed.add(x.dataset.theme);});themeOptions.forEach((o,i)=>{if(i===0){o.hidden=false;return;}o.hidden=!allowed.has(o.value);});if(theme.selectedOptions[0]&&theme.selectedOptions[0].hidden)theme.value='todos';}
 function apply(){const c=cat.value,s=sub.value,t=theme.value;let n=0;cards.forEach(x=>{const ok=cardHasCat(x,c)&&(s==='todos'||x.dataset.sub===s)&&(t==='todos'||x.dataset.theme===t)&&(!productFocus||x.dataset.product===productFocus);x.style.display=ok?'flex':'none';if(ok)n++;});count.textContent=n+' foto(s)';}
 cat.addEventListener('change',()=>{clearProductFocus();sub.value='todos';theme.value='todos';refreshSub();refreshTheme();apply();});
 sub.addEventListener('change',()=>{clearProductFocus();theme.value='todos';refreshTheme();apply();});theme.addEventListener('change',()=>{clearProductFocus();apply();});
 if(focusClear)focusClear.addEventListener('click',()=>{clearProductFocus();cat.value='todos';sub.value='todos';theme.value='todos';refreshSub();refreshTheme();apply();});
 window.alphaFestGalleryShowProduct=function(slug,label){productFocus=slug||'';cat.value='todos';sub.value='todos';theme.value='todos';refreshSub();refreshTheme();if(focus){focus.hidden=!productFocus;}if(focusLabel)focusLabel.textContent=label||'Produto';apply();const alvo=document.getElementById('galeria');if(alvo)alvo.scrollIntoView({behavior:'smooth',block:'start'});};
 document.querySelectorAll('.gallery-proof-btn').forEach(btn=>btn.addEventListener('click',()=>window.alphaFestGalleryShowProduct(btn.dataset.galleryProduct||'',btn.dataset.galleryLabel||'Produto')));
 photoButtons.forEach(btn=>btn.addEventListener('click',()=>openLightbox(btn)));
 if(lightboxClose)lightboxClose.addEventListener('click',closeLightbox);
 if(lightboxBackdrop)lightboxBackdrop.addEventListener('click',closeLightbox);
 if(lightboxPrev)lightboxPrev.addEventListener('click',()=>moveLightbox(-1));
 if(lightboxNext)lightboxNext.addEventListener('click',()=>moveLightbox(1));
 document.addEventListener('keydown',e=>{if(!lightbox||lightbox.hidden)return;if(e.key==='Escape'){e.preventDefault();closeLightbox();}else if(e.key==='ArrowLeft'){e.preventDefault();moveLightbox(-1);}else if(e.key==='ArrowRight'){e.preventDefault();moveLightbox(1);}});
 refreshSub();refreshTheme();apply();
})();
'''
    return {"html": secao, "css": css, "js": js, "resumo": resumo, "fotos_renderizadas": total_renderizado}
