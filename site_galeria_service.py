"""Galeria pública de trabalhos AlphaFest — prévia HF47.1.

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
        normalizado["subcategoria"] = _texto(item.get("subcategoria")) or "Sem subcategoria"
        normalizado["tema"] = _texto(item.get("tema"))
        normalizado["cor"] = _texto(item.get("cor"))
        normalizado["ocasiao"] = _texto(item.get("ocasiao"))
        saida.append(normalizado)
    # Os trabalhos mais novos aparecem primeiro, sem depender de um formato de data específico.
    return list(reversed(saida))


def resumir_galeria_site(galeria: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    trabalhos = selecionar_trabalhos_site(galeria)
    categorias = sorted({_texto(x.get("categoria")) for x in trabalhos if _texto(x.get("categoria"))}, key=str.casefold)
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
    for trabalho in trabalhos:
        produto = _texto(trabalho.get("produto")) or "Trabalho personalizado"
        categoria = _texto(trabalho.get("categoria")) or "Sem categoria"
        subcategoria = _texto(trabalho.get("subcategoria")) or "Sem subcategoria"
        tema = _texto(trabalho.get("tema"))
        cor = _texto(trabalho.get("cor"))
        ocasiao = _texto(trabalho.get("ocasiao"))
        detalhes = [x for x in [tema, cor, ocasiao] if x]
        detalhe_html = " • ".join(html.escape(x) for x in detalhes)
        mensagem = f"Olá! Vi este trabalho na Galeria da AlphaFest e gostaria de algo parecido: {produto}."
        if tema:
            mensagem += f" Tema: {tema}."
        if ocasiao:
            mensagem += f" Ocasião: {ocasiao}."
        mensagem += " Quero definir os detalhes, quantidade e prazo."
        href = f"https://wa.me/{numero}?text={quote(mensagem)}" if numero else "#"
        busca = " ".join([produto, categoria, subcategoria, tema, cor, ocasiao])
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
            imagem = (
                f'<img src="{html.escape(src, quote=True)}" alt="{html.escape(produto, quote=True)}" loading="lazy" decoding="async">'
                if src else '<div class="gallery-placeholder">AlphaFest</div>'
            )
            tema_slug = _slug(tema) if tema else "sem-tema"
            cards.append(
                f'''<article class="gallery-card" data-cat="{html.escape(_slug(categoria), quote=True)}" data-sub="{html.escape(_slug(subcategoria), quote=True)}" data-theme="{html.escape(tema_slug, quote=True)}" data-search="{html.escape(busca, quote=True)}">
                <div class="gallery-photo">{imagem}</div>
                <div class="gallery-body"><div class="gallery-tax">{html.escape(categoria)} <span>›</span> {html.escape(subcategoria)}</div>
                <h3>{html.escape(produto)}</h3>{f'<p>{detalhe_html}</p>' if detalhe_html else '<p>Personalizado produzido pela AlphaFest.</p>'}
                <a class="gallery-cta" href="{html.escape(href, quote=True)}" target="_blank" rel="noopener">💬 Quero algo parecido</a></div></article>'''
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
      <div class="gallery-toolbar" aria-label="Filtros da galeria">
        <label><span>Categoria</span><select id="gallery-cat">{''.join(options_categoria)}</select></label>
        <label><span>Subcategoria</span><select id="gallery-sub">{''.join(options_sub)}</select></label>
        <label><span>Tema</span><select id="gallery-theme">{''.join(options_tema)}</select></label>
        <div class="gallery-count" id="gallery-count">{total_renderizado} foto(s)</div>
      </div>
      <div class="gallery-grid" id="gallery-grid">{''.join(cards) if cards else vazio}</div>{aviso_limite}
    </div></section>'''

    css = r'''
.gallery-section{background:linear-gradient(180deg,#fff8fc,#ffffff)}
.gallery-toolbar{display:grid;grid-template-columns:1fr 1fr 1fr auto;gap:12px;align-items:end;margin:26px 0 22px;padding:16px;border:1px solid var(--line);border-radius:18px;background:#fff;box-shadow:0 8px 26px rgba(20,37,61,.04)}
.gallery-toolbar label span{display:block;font-size:11px;font-weight:900;letter-spacing:.05em;text-transform:uppercase;color:#617791;margin:0 0 6px}.gallery-toolbar select{width:100%;border:1px solid #cfe0ee;border-radius:11px;background:#fff;color:var(--ink);padding:11px 12px;font-size:14px;font-weight:750;outline:none}.gallery-count{min-width:105px;text-align:center;padding:12px 13px;border-radius:11px;background:#eef7ff;color:var(--blue);font-weight:900;font-size:13px}
.gallery-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.gallery-card{border:1px solid var(--line);border-radius:18px;overflow:hidden;background:#fff;box-shadow:0 10px 28px rgba(20,37,61,.06);display:flex;flex-direction:column}.gallery-photo{aspect-ratio:4/3;background:var(--soft);overflow:hidden}.gallery-photo img{width:100%;height:100%;object-fit:cover;display:block}.gallery-placeholder{height:100%;display:flex;align-items:center;justify-content:center;color:#84a9ca;font-size:24px;font-weight:950}.gallery-body{padding:15px;display:flex;flex-direction:column;flex:1}.gallery-tax{font-size:10px;text-transform:uppercase;letter-spacing:.06em;font-weight:900;color:var(--blue)}.gallery-tax span{color:#92a6b8}.gallery-body h3{font-size:18px;line-height:1.18;margin:7px 0 7px}.gallery-body p{font-size:13px;line-height:1.45;color:#647991;margin:0 0 14px;flex:1}.gallery-cta{display:flex;justify-content:center;align-items:center;min-height:42px;border-radius:10px;background:var(--green);color:#fff;text-decoration:none;font-size:13px;font-weight:900}.gallery-empty{grid-column:1/-1;border:1px dashed #cbddea;border-radius:16px;padding:42px;text-align:center;color:#637993;background:#fff}.gallery-preview-note{margin-top:14px;color:#73869b;font-size:11px;text-align:center}
@media(max-width:900px){.gallery-toolbar{grid-template-columns:1fr 1fr}.gallery-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.gallery-count{align-self:stretch;display:flex;align-items:center;justify-content:center}}
@media(max-width:620px){.gallery-toolbar{grid-template-columns:1fr;padding:13px}.gallery-toolbar select{font-size:16px;min-height:46px}.gallery-count{min-height:44px}.gallery-grid{grid-template-columns:1fr;gap:15px}.gallery-card{border-radius:16px}.gallery-body{padding:14px}.gallery-body h3{font-size:18px}.gallery-cta{min-height:46px}}
'''

    # O JS é isolado por IDs/classes gallery-* para não interferir nos filtros de Produtos.
    js = r'''
(function(){
 const cat=document.getElementById('gallery-cat'),sub=document.getElementById('gallery-sub'),theme=document.getElementById('gallery-theme'),count=document.getElementById('gallery-count');
 if(!cat||!sub||!theme||!count)return;
 const cards=[...document.querySelectorAll('.gallery-card')], subOptions=[...sub.options], themeOptions=[...theme.options];
 function refreshSub(){const c=cat.value;subOptions.forEach((o,i)=>{if(i===0){o.hidden=false;return;}o.hidden=(c!=='todos'&&o.dataset.parent!==c);});if(sub.selectedOptions[0]&&sub.selectedOptions[0].hidden)sub.value='todos';}
 function refreshTheme(){const c=cat.value,s=sub.value,allowed=new Set();cards.forEach(x=>{if((c==='todos'||x.dataset.cat===c)&&(s==='todos'||x.dataset.sub===s))allowed.add(x.dataset.theme);});themeOptions.forEach((o,i)=>{if(i===0){o.hidden=false;return;}o.hidden=!allowed.has(o.value);});if(theme.selectedOptions[0]&&theme.selectedOptions[0].hidden)theme.value='todos';}
 function apply(){const c=cat.value,s=sub.value,t=theme.value;let n=0;cards.forEach(x=>{const ok=(c==='todos'||x.dataset.cat===c)&&(s==='todos'||x.dataset.sub===s)&&(t==='todos'||x.dataset.theme===t);x.style.display=ok?'flex':'none';if(ok)n++;});count.textContent=n+' foto(s)';}
 cat.addEventListener('change',()=>{sub.value='todos';theme.value='todos';refreshSub();refreshTheme();apply();});
 sub.addEventListener('change',()=>{theme.value='todos';refreshTheme();apply();});theme.addEventListener('change',apply);refreshSub();refreshTheme();apply();
})();
'''
    return {"html": secao, "css": css, "js": js, "resumo": resumo, "fotos_renderizadas": total_renderizado}
