"""Prévia responsiva da futura vitrine pública AlphaFest (HF37).

Somente leitura: seleciona produtos diretamente do Catálogo oficial marcados
para o site e prontos para apresentação. Não persiste, publica ou altera dados.
"""
from __future__ import annotations

import html
import re
import unicodedata
from typing import Any, Callable, Dict, Iterable, List, Optional
from urllib.parse import quote

from site_manager_service import avaliar_produto_site


ImagemResolver = Optional[Callable[[str], str]]


def _slug(texto: str) -> str:
    base = unicodedata.normalize("NFKD", str(texto or ""))
    base = "".join(c for c in base if not unicodedata.combining(c))
    base = re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()
    return base or "sem-categoria"


def _lista(valor: Any) -> List[str]:
    if valor is None:
        return []
    if isinstance(valor, (str, bytes, bytearray)):
        valor = [valor]
    try:
        itens = list(valor)
    except TypeError:
        itens = [valor]
    return [str(x).strip() for x in itens if str(x or "").strip()]


def _preco_br(valor: Any) -> str:
    texto = str(valor or "").strip()
    if not texto:
        return "Sob consulta"
    limpo = re.sub(r"[^0-9,.-]", "", texto)
    try:
        if "," in limpo:
            numero = float(limpo.replace(".", "").replace(",", "."))
        else:
            numero = float(limpo)
        return f"R$ {numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return texto if texto.upper().startswith("R$") else f"R$ {texto}"


def selecionar_produtos_vitrine(catalogo: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Seleciona somente itens ativos, marcados e prontos, sem alterar a origem."""
    saida: List[Dict[str, Any]] = []
    for indice, produto in enumerate(catalogo or []):
        if not isinstance(produto, dict):
            continue
        leitura = avaliar_produto_site(produto)
        if not (leitura["ativo"] and leitura["publicar_site"] and leitura["pronto"]):
            continue
        item = dict(leitura)
        item["indice_catalogo"] = indice
        item["variacoes"] = _lista(produto.get("Variacoes"))
        item["subcategoria"] = str(produto.get("Subcategoria") or "").strip()
        item["material"] = str(produto.get("Material") or "").strip()
        saida.append(item)
    saida.sort(key=lambda x: (not bool(x.get("destaque")), str(x.get("categoria") or "").casefold(), str(x.get("nome") or "").casefold()))
    return saida


def resumir_vitrine(catalogo: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    produtos = selecionar_produtos_vitrine(catalogo)
    categorias = sorted({str(x.get("categoria") or "Outros").strip() or "Outros" for x in produtos}, key=str.casefold)
    return {
        "produtos": produtos,
        "total": len(produtos),
        "destaques": sum(1 for x in produtos if x.get("destaque")),
        "categorias": categorias,
        "total_categorias": len(categorias),
    }


def gerar_html_vitrine(
    catalogo: Iterable[Dict[str, Any]],
    empresa: Dict[str, Any],
    *,
    logo_src: str = "",
    imagem_resolver: ImagemResolver = None,
    modo_preview: bool = True,
) -> str:
    """Gera HTML autônomo da vitrine. Nenhuma publicação é realizada."""
    resumo = resumir_vitrine(catalogo)
    produtos = resumo["produtos"]
    categorias = resumo["categorias"]

    nome_empresa = str((empresa or {}).get("nome") or "AlphaFest").strip() or "AlphaFest"
    subtitulo = str((empresa or {}).get("subtitulo") or "Personalizados & Balões").strip()
    slogan = str((empresa or {}).get("slogan") or "O poder de estar presente em cada presente!").strip()
    cidade = str((empresa or {}).get("cidade") or "").strip()
    uf = str((empresa or {}).get("uf") or "").strip()
    local = " · ".join(x for x in [cidade, uf] if x)
    numero = re.sub(r"\D", "", str((empresa or {}).get("whatsapp_catalogo") or (empresa or {}).get("celular") or ""))
    if numero and not numero.startswith("55"):
        numero = "55" + numero
    mensagem_geral = quote("Olá! Vim pelo site da AlphaFest e gostaria de fazer um orçamento.")
    whatsapp_geral = f"https://wa.me/{numero}?text={mensagem_geral}" if numero else "#"

    chips = ['<button class="filter active" data-cat="todos">Todos</button>']
    for cat in categorias:
        chips.append(f'<button class="filter" data-cat="{html.escape(_slug(cat), quote=True)}">{html.escape(cat)}</button>')

    cards: List[str] = []
    for item in produtos:
        nome = str(item.get("nome") or "Produto").strip() or "Produto"
        descricao = str(item.get("descricao") or "").strip()
        categoria = str(item.get("categoria") or "Outros").strip() or "Outros"
        exibir_preco = bool(item.get("exibir_preco_site")) and bool(str(item.get("preco") or "").strip())
        preco = _preco_br(item.get("preco")) if exibir_preco else ""
        img = str(item.get("imagem_principal") or "").strip()
        if img and imagem_resolver is not None:
            try:
                resolvida = str(imagem_resolver(img) or "").strip()
                if resolvida:
                    img = resolvida
                elif not img.startswith(("http://", "https://", "data:image/")):
                    # Nunca expor caminho interno/local na prévia exportável.
                    img = ""
            except Exception:
                if not img.startswith(("http://", "https://", "data:image/")):
                    img = ""
        imagem_html = (
            f'<img src="{html.escape(img, quote=True)}" alt="{html.escape(nome, quote=True)}" loading="lazy">'
            if img else '<div class="placeholder">AlphaFest</div>'
        )
        opcoes = item.get("variacoes") or []
        opcoes_html = ""
        if opcoes:
            texto_opcoes = " • ".join(opcoes[:5]) + (" …" if len(opcoes) > 5 else "")
            opcoes_html = f'<div class="options"><strong>Opções:</strong> {html.escape(texto_opcoes)}</div>'
        msg = quote(f"Olá! Vim pelo site da AlphaFest e gostaria de informações sobre: {nome}")
        href = f"https://wa.me/{numero}?text={msg}" if numero else "#"
        busca = " ".join([nome, descricao, categoria, item.get("subcategoria") or "", item.get("material") or ""])
        busca = unicodedata.normalize("NFKD", busca).encode("ascii", "ignore").decode("ascii").casefold()
        badge = '<span class="badge">⭐ Destaque</span>' if item.get("destaque") else ""
        descricao_curta = descricao[:280] + ("…" if len(descricao) > 280 else "")
        preco_html = f'<div class="price">{html.escape(preco)}</div>' if preco else ""
        footer_classe = "card-footer" if preco else "card-footer no-price"
        cards.append(
            f'''<article class="product-card" data-cat="{html.escape(_slug(categoria), quote=True)}" data-search="{html.escape(busca, quote=True)}">
                <div class="photo">{imagem_html}{badge}</div>
                <div class="card-body">
                    <div class="category">{html.escape(categoria)}</div>
                    <h3>{html.escape(nome)}</h3>
                    <p>{html.escape(descricao_curta)}</p>
                    {opcoes_html}
                    <div class="{footer_classe}">{preco_html}<a class="cta small" href="{html.escape(href, quote=True)}" target="_blank" rel="noopener">Pedir orçamento</a></div>
                </div>
            </article>'''
        )

    logo = f'<img class="brand-logo" src="{html.escape(str(logo_src), quote=True)}" alt="AlphaFest">' if logo_src else '<div class="brand-word">AlphaFest</div>'
    preview_bar = '<div class="preview-bar">PRÉVIA INTERNA HF37 · AINDA NÃO PUBLICADA</div>' if modo_preview else ""
    vazio = '<div class="empty">Nenhum produto pronto está marcado para o site.</div>' if not cards else ""

    return f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(nome_empresa)} · {html.escape(subtitulo)}</title>
<style>
:root{{--blue:#0b67c6;--cyan:#2db7e5;--pink:#f44f8d;--ink:#14253d;--soft:#f4faff;--line:#dbe9f5;--green:#25d366}}
*{{box-sizing:border-box}} html{{scroll-behavior:smooth}} body{{margin:0;font-family:Inter,Arial,Helvetica,sans-serif;color:var(--ink);background:#fff}}
.preview-bar{{background:#15233a;color:#fff;text-align:center;font-size:11px;font-weight:800;letter-spacing:.08em;padding:8px 12px}}
.header{{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.96);backdrop-filter:blur(12px);border-bottom:1px solid var(--line)}}
.header-in{{max-width:1240px;margin:auto;padding:12px 22px;display:flex;align-items:center;gap:18px}} .brand{{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--ink)}}
.brand-logo{{width:68px;height:54px;object-fit:contain}} .brand-word{{font-size:26px;font-weight:900;color:var(--blue)}} .brand-copy strong{{display:block;font-size:16px}} .brand-copy span{{font-size:12px;color:#60748e}}
.header-actions{{margin-left:auto;display:flex;gap:10px;align-items:center}} .ghost{{color:var(--blue);text-decoration:none;font-weight:800;padding:10px 12px}}
.cta{{display:inline-flex;align-items:center;justify-content:center;background:var(--green);color:#fff;text-decoration:none;font-weight:900;border-radius:12px;padding:12px 17px;box-shadow:0 7px 18px rgba(37,211,102,.22)}} .cta.small{{padding:9px 12px;font-size:13px;border-radius:9px}}
.hero{{background:radial-gradient(circle at 88% 12%,rgba(244,79,141,.18),transparent 25%),radial-gradient(circle at 10% 75%,rgba(45,183,229,.24),transparent 30%),linear-gradient(135deg,#f8fcff,#fff 48%,#fff7fb);border-bottom:1px solid var(--line)}}
.hero-in{{max-width:1240px;margin:auto;padding:58px 22px 48px;display:grid;grid-template-columns:1.35fr .65fr;gap:40px;align-items:center}}
.eyebrow{{color:var(--blue);font-size:13px;font-weight:900;text-transform:uppercase;letter-spacing:.1em}} .hero h1{{font-size:clamp(38px,6vw,72px);line-height:.98;margin:12px 0 18px;letter-spacing:-.04em}} .hero h1 span{{background:linear-gradient(90deg,var(--blue),var(--cyan),var(--pink));-webkit-background-clip:text;background-clip:text;color:transparent}}
.hero p{{font-size:18px;line-height:1.6;color:#50657f;max-width:720px}} .hero-actions{{display:flex;flex-wrap:wrap;gap:12px;margin-top:24px}} .secondary{{display:inline-flex;text-decoration:none;color:var(--ink);border:1px solid var(--line);background:#fff;padding:12px 17px;border-radius:12px;font-weight:850}}
.hero-card{{background:#fff;border:1px solid var(--line);border-radius:24px;padding:26px;box-shadow:0 24px 60px rgba(11,103,198,.12)}} .hero-stat{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}} .stat{{padding:16px;border-radius:16px;background:var(--soft)}} .stat strong{{display:block;font-size:28px;color:var(--blue)}} .stat span{{font-size:12px;color:#60748e}}
.main{{max-width:1240px;margin:auto;padding:36px 22px 70px}} .toolbar{{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:18px}} .search{{flex:1;min-width:260px;position:relative}} .search input{{width:100%;border:1px solid var(--line);border-radius:14px;padding:14px 16px 14px 42px;font-size:15px;outline:none;background:#fff}} .search:before{{content:'🔎';position:absolute;left:14px;top:13px}}
.filters{{display:flex;gap:8px;overflow-x:auto;padding:2px 0 14px;scrollbar-width:thin}} .filter{{border:1px solid var(--line);background:#fff;color:var(--ink);padding:9px 13px;border-radius:999px;white-space:nowrap;font-weight:800;cursor:pointer}} .filter.active{{background:var(--blue);border-color:var(--blue);color:#fff}}
.section-head{{display:flex;justify-content:space-between;gap:18px;align-items:end;margin:20px 0}} .section-head h2{{font-size:30px;margin:0}} .section-head p{{margin:5px 0 0;color:#667b94}} #result-count{{font-weight:800;color:var(--blue);white-space:nowrap}}
.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:22px}} .product-card{{border:1px solid var(--line);border-radius:20px;overflow:hidden;background:#fff;box-shadow:0 10px 30px rgba(20,37,61,.06);display:flex;flex-direction:column;transition:.18s}} .product-card:hover{{transform:translateY(-3px);box-shadow:0 16px 36px rgba(20,37,61,.11)}}
.photo{{position:relative;background:var(--soft);aspect-ratio:4/3;overflow:hidden}} .photo img{{width:100%;height:100%;object-fit:cover;display:block}} .placeholder{{height:100%;display:flex;align-items:center;justify-content:center;font-size:28px;font-weight:900;color:#84a9ca}} .badge{{position:absolute;top:12px;left:12px;background:#fff;color:#a26100;border-radius:999px;padding:7px 10px;font-size:11px;font-weight:900;box-shadow:0 3px 12px rgba(0,0,0,.12)}}
.card-body{{padding:18px;display:flex;flex-direction:column;flex:1}} .category{{font-size:11px;text-transform:uppercase;letter-spacing:.08em;font-weight:900;color:var(--blue)}} .card-body h3{{font-size:20px;line-height:1.15;margin:7px 0 10px}} .card-body p{{font-size:14px;line-height:1.55;color:#60748e;margin:0 0 12px;flex:1}} .options{{font-size:12px;color:#60748e;margin:0 0 12px}} .card-footer{{display:flex;gap:10px;align-items:center;justify-content:space-between;border-top:1px solid #edf3f8;padding-top:14px}} .card-footer.no-price .cta{{width:100%}} .price{{font-weight:950;font-size:17px}}
.empty{{padding:50px;text-align:center;border:1px dashed var(--line);border-radius:18px;color:#60748e}} .footer{{background:#10243c;color:#d7e8f7}} .footer-in{{max-width:1240px;margin:auto;padding:34px 22px;display:flex;gap:24px;justify-content:space-between;align-items:center}} .footer strong{{color:#fff}} .footer small{{color:#9fb7cb}}
@media(max-width:900px){{.hero-in{{grid-template-columns:1fr}}.hero-card{{display:none}}.grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}
@media(max-width:620px){{.brand-copy{{display:none}}.ghost{{display:none}}.header-in{{padding:9px 14px}}.brand-logo{{width:58px;height:46px}}.hero-in{{padding:36px 16px 32px}}.hero h1{{font-size:42px}}.hero p{{font-size:16px}}.main{{padding:26px 14px 55px}}.grid{{grid-template-columns:1fr}}.section-head{{align-items:flex-start;flex-direction:column}}.product-card{{border-radius:16px}}.footer-in{{flex-direction:column;align-items:flex-start}}}}
</style></head>
<body>{preview_bar}
<header class="header"><div class="header-in"><a class="brand" href="#inicio">{logo}<div class="brand-copy"><strong>{html.escape(nome_empresa)}</strong><span>{html.escape(subtitulo)}</span></div></a><div class="header-actions"><a class="ghost" href="#produtos">Ver produtos</a><a class="cta" href="{html.escape(whatsapp_geral, quote=True)}" target="_blank" rel="noopener">💬 Falar no WhatsApp</a></div></div></header>
<section class="hero" id="inicio"><div class="hero-in"><div><div class="eyebrow">Personalização que vira presença</div><h1>Seu evento, sua marca, <span>do seu jeito.</span></h1><p>{html.escape(slogan)} Escolha uma ideia na vitrine e fale com a AlphaFest para personalizar detalhes, quantidade e prazo.</p><div class="hero-actions"><a class="cta" href="{html.escape(whatsapp_geral, quote=True)}" target="_blank" rel="noopener">💬 Quero um orçamento</a><a class="secondary" href="#produtos">Explorar produtos ↓</a></div></div><aside class="hero-card"><div class="eyebrow">Vitrine AlphaFest</div><h2>Personalizados & Balões</h2><p>Produtos selecionados diretamente do Catálogo oficial do Manager.</p><div class="hero-stat"><div class="stat"><strong>{resumo['total']}</strong><span>produtos na vitrine</span></div><div class="stat"><strong>{resumo['total_categorias']}</strong><span>categorias</span></div></div></aside></div></section>
<main class="main" id="produtos"><div class="section-head"><div><h2>Encontre seu personalizado</h2><p>Pesquise ou filtre por categoria.</p></div><div id="result-count">{resumo['total']} produto(s)</div></div><div class="toolbar"><label class="search"><input id="search" type="search" placeholder="Buscar produto, categoria ou descrição..."></label></div><div class="filters">{''.join(chips)}</div><div class="grid" id="grid">{''.join(cards)}</div>{vazio}</main>
<footer class="footer"><div class="footer-in"><div><strong>{html.escape(nome_empresa)}</strong><br><small>{html.escape(subtitulo)}{(' · ' + html.escape(local)) if local else ''}</small></div><div>{html.escape(slogan)}</div></div></footer>
<script>
(function(){{let cat='todos';const cards=[...document.querySelectorAll('.product-card')];const input=document.getElementById('search');const count=document.getElementById('result-count');function norm(s){{return (s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();}}function apply(){{const q=norm(input.value);let n=0;cards.forEach(c=>{{const okCat=cat==='todos'||c.dataset.cat===cat;const okQ=!q||norm(c.dataset.search).includes(q);const ok=okCat&&okQ;c.style.display=ok?'flex':'none';if(ok)n++;}});count.textContent=n+' produto(s)';}}document.querySelectorAll('.filter').forEach(b=>b.addEventListener('click',()=>{{document.querySelectorAll('.filter').forEach(x=>x.classList.remove('active'));b.classList.add('active');cat=b.dataset.cat;apply();}}));input.addEventListener('input',apply);apply();}})();
</script></body></html>'''
