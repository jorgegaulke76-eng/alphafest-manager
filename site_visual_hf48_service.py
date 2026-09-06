"""HF48 — camada visual comercial do site AlphaFest (HF49.1 · base visual HF48.3-HF4).

Aplica somente apresentação/UX sobre o HTML já gerado pelos serviços HF40-HF47.
Não altera Catálogo, Galeria, publicação Cloudflare, dados ou Fonte Única.
O recurso é opt-in e usado inicialmente apenas em prévia interna.
"""
from __future__ import annotations

import base64
import html
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List

from site_vitrine_service import ImagemResolver, resumir_vitrine


ICONES_CATEGORIA = {
    "festa": "🎉",
    "personal": "🎨",
    "balao": "🎈",
    "decor": "✨",
    "graf": "🖨️",
    "brinde": "🎁",
    "convite": "💌",
    "papel": "📄",
    "3d": "🧊",
    "laser": "⚡",
    "caneca": "☕",
    "copo": "🥤",
    "adesivo": "🏷️",
}


def _slug(texto: str) -> str:
    import unicodedata
    base = unicodedata.normalize("NFKD", str(texto or ""))
    base = "".join(c for c in base if not unicodedata.combining(c))
    base = re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()
    return base or "sem-categoria"


def _icone_categoria(nome: str) -> str:
    chave = _slug(nome).replace("-", " ")
    for termo, icone in ICONES_CATEGORIA.items():
        if termo in chave:
            return icone
    return "⭐"



def _asset_data_uri(nome: str) -> str:
    """Carrega um mascote local otimizado e devolve data URI para a prévia auto-contida."""
    caminho = Path(__file__).resolve().parent / "assets" / "mascotes" / nome
    try:
        dados = caminho.read_bytes()
    except OSError:
        return ""
    mime = "image/webp" if caminho.suffix.lower() == ".webp" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(dados).decode('ascii')}"


def _mascotes_hf48() -> Dict[str, str]:
    return {
        "hero": _asset_data_uri("thu_fox_hero.webp"),
        "galeria": _asset_data_uri("fox_galeria.webp"),
        "cta": _asset_data_uri("thu_fox_cta.webp"),
        "baloes": _asset_data_uri("baloes_hero.webp"),
        "logo_wordmark": _asset_data_uri("logo_wordmark_transparent.png"),
    }



def _resolver_imagem_site(valor: str, imagem_resolver: ImagemResolver = None) -> str:
    img = str(valor or "").strip()
    if not img:
        return ""
    if imagem_resolver is not None:
        try:
            resolvida = str(imagem_resolver(img) or "").strip()
            if resolvida:
                return resolvida
        except Exception:
            pass
    return img if img.startswith(("http://", "https://", "data:image/")) else ""


def _carrossel_html(
    catalogo: Iterable[Dict[str, Any]],
    *,
    imagem_resolver: ImagemResolver = None,
    mascotes: Dict[str, str] | None = None,
) -> str:
    """HF50.1-HF3 — carrossel promocional compacto, sem novo cadastro paralelo.

    Usa primeiro ``CarrosselSite`` (controle rápido no Catálogo). Enquanto nenhum
    item for marcado, cai nos produtos já marcados como Destaque, para que a área
    não fique vazia na primeira homologação.
    """
    resumo = resumir_vitrine(catalogo, usar_taxonomia_catalogo=True)
    produtos = list(resumo.get("produtos") or [])
    escolhidos = [p for p in produtos if bool(p.get("carrossel_site"))]
    origem = "selecionados"
    if not escolhidos:
        escolhidos = [p for p in produtos if bool(p.get("destaque"))]
        origem = "destaques"
    escolhidos = escolhidos[:5]
    if not escolhidos:
        return ""

    slides: List[str] = []
    dots: List[str] = []
    for i, item in enumerate(escolhidos):
        nome = str(item.get("nome") or "Produto AlphaFest").strip()
        cat = str(item.get("categoria_publica") or item.get("categoria") or "AlphaFest").strip()
        sub = str(item.get("subcategoria_publica") or item.get("subcategoria") or "").strip()
        descricao = str(item.get("descricao") or "").strip()
        if len(descricao) > 150:
            descricao = descricao[:147].rstrip() + "…"
        img = _resolver_imagem_site(str(item.get("imagem_principal") or ""), imagem_resolver)
        if img:
            img_html = f'<img class="hf50-carousel-product-img" src="{html.escape(img, quote=True)}" alt="{html.escape(nome, quote=True)}" loading="lazy">'
        else:
            img_html = '<div class="hf50-carousel-placeholder">AlphaFest</div>'
        etiqueta = "Destaque escolhido" if bool(item.get("carrossel_site")) else "Destaque AlphaFest"
        tax = " · ".join(x for x in (cat, sub) if x)
        aria = "false" if i == 0 else "true"
        slides.append(
            f'<article class="hf50-carousel-slide" data-hf50-slide="{i}" aria-hidden="{aria}">'
            f'<div class="hf50-carousel-copy"><span class="hf50-carousel-kicker">✨ {html.escape(etiqueta)}</span><h2>{html.escape(nome)}</h2>'
            f'<div class="hf50-carousel-tax">{html.escape(tax)}</div><p>{html.escape(descricao or "Uma ideia AlphaFest para personalizar do seu jeito.")}</p>'
            f'<div class="hf50-carousel-actions"><button type="button" class="hf50-carousel-product" data-hf50-product="{html.escape(nome, quote=True)}">Ver produto</button><button type="button" class="hf50-carousel-whatsapp" data-site-scroll="contato">💬 Pedir orçamento</button></div></div>'
            f'<div class="hf50-carousel-media">{img_html}</div></article>'
        )
        ativo = " active" if i == 0 else ""
        dots.append(f'<button type="button" class="hf50-carousel-dot{ativo}" data-hf50-dot="{i}" aria-label="Ir para destaque {i+1}"></button>')

    fox = ""
    if mascotes and mascotes.get("galeria"):
        fox = f'<img class="hf50-carousel-fox" src="{mascotes["galeria"]}" alt="Fox, mascote AlphaFest">'
    return (
        f'<section class="hf50-carousel" id="destaques"><div class="hf50-carousel-shell">{fox}'
        f'<div class="hf50-carousel-viewport"><div class="hf50-carousel-track">{"".join(slides)}</div></div>'
        '<button type="button" class="hf50-carousel-arrow prev" aria-label="Destaque anterior">‹</button>'
        '<button type="button" class="hf50-carousel-arrow next" aria-label="Próximo destaque">›</button>'
        f'<div class="hf50-carousel-dots">{"".join(dots)}</div></div></section>'
    )

def _categorias_html(catalogo: Iterable[Dict[str, Any]]) -> str:
    resumo = resumir_vitrine(catalogo, usar_taxonomia_catalogo=True)
    categorias: List[str] = list(resumo.get("categorias") or [])
    contagens = dict(resumo.get("contagem_por_categoria") or {})
    if not categorias:
        return ""
    cards = []
    for cat in categorias[:12]:
        qtd = int(contagens.get(cat, 0) or 0)
        cards.append(
            f'''<button type="button" class="hf48-category-card" data-hf48-cat="{html.escape(_slug(cat), quote=True)}">
              <span class="hf48-cat-icon">{_icone_categoria(cat)}</span>
              <span class="hf48-cat-copy"><strong>{html.escape(cat)}</strong><small>{qtd} produto(s)</small></span>
              <span class="hf48-cat-arrow">›</span>
            </button>'''
        )
    return f'''<section class="hf48-categories" id="categorias"><div class="hf48-wrap">
      <div class="hf48-section-heading"><div><span class="hf48-kicker">Encontre mais rápido</span><h2>Explore por categoria</h2><p>Escolha o tipo de produto e vá direto às opções disponíveis na vitrine.</p></div><button type="button" class="hf48-text-link" data-site-scroll="produtos">Ver todos os produtos →</button></div>
      <div class="hf48-category-grid">{''.join(cards)}</div>
    </div></section>'''


def aplicar_visual_hf48(
    pagina: str,
    catalogo: Iterable[Dict[str, Any]],
    empresa: Dict[str, Any],
    *,
    incluir_galeria: bool = False,
    usar_mascotes: bool = False,
    imagem_resolver: ImagemResolver = None,
) -> str:
    """Retorna uma cópia visualmente reestilizada do site já gerado.

    A transformação não persiste nada e não é executada quando o chamador não
    passa ``visual_hf48=True`` no serviço principal.
    """
    catalogo = list(catalogo or [])
    empresa = dict(empresa or {})
    resumo = resumir_vitrine(catalogo, usar_taxonomia_catalogo=True)
    total = int(resumo.get("total", 0) or 0)
    total_categorias = int(resumo.get("total_categorias", 0) or 0)
    nome = str(empresa.get("nome") or "AlphaFest").strip() or "AlphaFest"
    slogan = str(empresa.get("slogan") or "O poder de estar presente em cada presente!").strip()
    mascotes = _mascotes_hf48() if usar_mascotes else {"hero": "", "galeria": "", "cta": "", "baloes": "", "logo_wordmark": ""}

    css = r'''
/* HF48.1 — nova linguagem visual comercial (somente opt-in) */
:root{--hf48-navy:#10264d;--hf48-blue:#0678df;--hf48-cyan:#14b9f4;--hf48-pink:#ff2f91;--hf48-yellow:#ffd21f;--hf48-green:#33cf69;--hf48-orange:#ff8b1f;--hf48-sky:#eaf8ff;--hf48-bg:#f8fbff;--hf48-border:#dfeaf5}
body{background:var(--hf48-bg)}
.hf48-topline{background:linear-gradient(90deg,#0459b6,#057de2 45%,#12a9e9);color:#fff;text-align:center;padding:8px 16px;font-size:12px;font-weight:800;letter-spacing:.01em}
.header{position:sticky;top:0;background:#fff;border-bottom:1px solid var(--hf48-border);box-shadow:0 4px 18px rgba(18,35,61,.05)}
.header-in{max-width:1320px;padding:14px 24px}.brand-logo{width:74px;height:58px}.brand-copy strong{font-size:28px;font-weight:950;background:linear-gradient(90deg,#0876d8 0%,#14b9f4 28%,#33cf69 46%,#ffd21f 63%,#ff8b1f 76%,#ff2f91 100%);-webkit-background-clip:text;background-clip:text;color:transparent}.brand-copy span{font-size:12px}
.hf48-header-search{flex:1;max-width:610px;margin-left:22px;display:flex;align-items:center;border:1px solid #d9e3ee;border-radius:15px;background:#f8fbfe;overflow:hidden;min-height:48px}
.hf48-header-search input{flex:1;border:0;outline:0;background:transparent;padding:0 16px;font-size:14px;color:var(--ink)}.hf48-header-search button{border:0;background:linear-gradient(135deg,var(--hf48-blue),var(--hf48-cyan));color:#fff;font-weight:900;align-self:stretch;padding:0 20px;cursor:pointer}
.header-actions .ghost{display:none}.header-actions .cta{border-radius:14px;padding:13px 18px}
.site-nav{top:87px;background:#fff;border-bottom:1px solid var(--hf48-border)}.site-nav-in{max-width:1320px;justify-content:flex-start;padding:0 24px}.site-nav a,.site-nav button{font-size:13px;padding:13px 14px}.site-nav a:hover,.site-nav button:hover{background:#eef7ff}
.hero{position:relative;overflow:hidden;background:linear-gradient(135deg,#eaf8ff 0%,#fff 48%,#fff0fa 100%);border-bottom:0}.hero:before{content:'';position:absolute;left:-95px;top:34px;width:230px;height:230px;border-radius:48% 52% 58% 42%;background:linear-gradient(145deg,rgba(20,185,244,.32),rgba(6,120,223,.08));transform:rotate(18deg)}.hero:after{content:'';position:absolute;right:-80px;bottom:-80px;width:230px;height:230px;border-radius:50%;background:linear-gradient(145deg,rgba(255,47,145,.22),rgba(255,210,31,.10))}.hero-in{max-width:1320px;padding:64px 24px 58px;grid-template-columns:1.08fr .92fr;gap:46px}.hero.hf48-hero-branded:before,.hero.hf48-hero-branded:after{display:none}.hero.hf48-hero-branded .hero-in{position:relative;z-index:2}.hf48-real-balloons{position:absolute;left:-18px;top:76px;width:150px;height:auto;z-index:1;pointer-events:none;filter:drop-shadow(0 12px 18px rgba(17,72,126,.10))}.hero h1{font-size:clamp(42px,5.6vw,76px);line-height:.98}.hero h1 span{background:linear-gradient(90deg,#0876d8 0%,#14b9f4 32%,#ff2f91 70%,#ff8b1f 100%);-webkit-background-clip:text;background-clip:text;color:transparent}.hero p{max-width:650px}.hero-card{border:1px solid rgba(255,255,255,.85);border-radius:28px;background:rgba(255,255,255,.88);backdrop-filter:blur(4px);box-shadow:0 28px 70px rgba(18,35,61,.13);padding:30px;position:relative;overflow:hidden}.hero-card:after{content:'';position:absolute;width:160px;height:160px;border-radius:50%;background:linear-gradient(135deg,rgba(8,118,216,.13),rgba(255,79,145,.14));right:-42px;top:-48px}.hero-card h2{font-size:28px;margin:8px 0 10px}.hero-stat{position:relative;z-index:2}.stat{background:#f4f9fe;border:1px solid #e8f0f7}.stat strong{font-size:32px}.secondary{border-color:#d8e3ee;border-radius:13px}
.hf48-trust{display:flex;gap:8px;flex-wrap:wrap;margin-top:20px}.hf48-trust span{background:rgba(255,255,255,.82);border:1px solid #dce8f3;border-radius:999px;padding:8px 11px;font-size:12px;font-weight:800;color:#526a83}
.hf48-wrap{max-width:1320px;margin:auto}.hf48-categories{background:#fff;padding:48px 24px}.hf48-section-heading{display:flex;align-items:end;justify-content:space-between;gap:24px;margin-bottom:22px}.hf48-section-heading h2{font-size:34px;margin:4px 0 6px}.hf48-section-heading p{margin:0;color:#657a92}.hf48-kicker{color:var(--hf48-blue);font-size:12px;font-weight:950;text-transform:uppercase;letter-spacing:.09em}.hf48-text-link{border:0;background:transparent;color:var(--hf48-blue);font-weight:900;cursor:pointer;white-space:nowrap}.hf48-category-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.hf48-category-card{border:1px solid var(--hf48-border);background:#fff;border-radius:18px;padding:16px;display:flex;align-items:center;gap:12px;text-align:left;cursor:pointer;transition:.18s;box-shadow:0 6px 20px rgba(18,35,61,.035)}.hf48-category-card:hover{transform:translateY(-2px);border-color:#afd7f8;box-shadow:0 12px 28px rgba(18,35,61,.08)}.hf48-cat-icon{width:46px;height:46px;border-radius:14px;background:#edf8ff;display:flex;align-items:center;justify-content:center;font-size:23px}.hf48-category-card:nth-child(4n+1) .hf48-cat-icon{background:#e5f7ff}.hf48-category-card:nth-child(4n+2) .hf48-cat-icon{background:#ffe8f3}.hf48-category-card:nth-child(4n+3) .hf48-cat-icon{background:#fff6cc}.hf48-category-card:nth-child(4n) .hf48-cat-icon{background:#e8fff1}.hf48-hero-benefits{position:relative;z-index:3;display:grid;gap:8px;margin-top:14px;max-width:330px}.hf48-hero-benefit{display:flex;align-items:center;gap:10px;border:1px solid #e2ecf6;border-radius:999px;background:rgba(255,255,255,.90);padding:9px 12px;font-size:12px;font-weight:850;color:#173d66}.hf48-hero-benefit b{display:flex;width:28px;height:28px;border-radius:50%;align-items:center;justify-content:center;font-size:15px}.hf48-hero-benefit:nth-child(1) b{background:#ffe7f2}.hf48-hero-benefit:nth-child(2) b{background:#fff5c7}.hf48-hero-benefit:nth-child(3) b{background:#e4f7ff}.hf48-cat-copy{min-width:0;flex:1}.hf48-cat-copy strong{display:block;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.hf48-cat-copy small{display:block;margin-top:4px;color:#75889e}.hf48-cat-arrow{font-size:24px;color:#9db1c5}
.main{max-width:1320px;padding:48px 24px 76px}.section-head{margin-top:0}.section-head h2{font-size:34px}.toolbar{background:#fff;border:1px solid var(--hf48-border);padding:10px;border-radius:18px;box-shadow:0 8px 26px rgba(18,35,61,.04)}.search input{border:0;background:#f8fbfd;border-radius:12px}.taxonomy-step{border-color:var(--hf48-border);box-shadow:0 6px 20px rgba(18,35,61,.025)}
.grid{grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}.product-card{border-color:var(--hf48-border);border-radius:18px;box-shadow:0 8px 24px rgba(18,35,61,.055)}.product-card:hover{box-shadow:0 16px 32px rgba(18,35,61,.105)}.photo{aspect-ratio:1/1}.card-body{padding:15px}.card-body h3{font-size:17px}.card-body p{font-size:13px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}.cta.small{border-radius:11px}
.site-section{padding-top:64px;padding-bottom:64px}.site-section.alt,.site-section.pink{background:#fff}.services-grid{gap:12px}.service-card{box-shadow:0 7px 22px rgba(18,35,61,.045);border-color:var(--hf48-border)}
.hf48-process{background:linear-gradient(120deg,#12233d,#173b67);color:#fff;padding:58px 24px}.hf48-process .hf48-section-heading h2,.hf48-process .hf48-section-heading p{color:#fff}.hf48-process-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.hf48-process-card{border:1px solid rgba(255,255,255,.14);background:rgba(255,255,255,.075);border-radius:18px;padding:20px}.hf48-process-card b{display:flex;width:34px;height:34px;border-radius:50%;align-items:center;justify-content:center;background:#fff;color:#173b67;margin-bottom:12px}.hf48-process-card strong{display:block;font-size:16px}.hf48-process-card span{display:block;margin-top:7px;color:#c9d8e8;font-size:13px;line-height:1.5}
.gallery-section{background:#fff!important}
.footer{background:#0d1c31}.footer-in{max-width:1320px;padding:40px 24px}
/* HF48.2 — Thu + Fox como assinatura visual, sem alterar a operação */
.hero{background:
  radial-gradient(circle at 3% 28%,rgba(20,185,244,.22) 0 7%,transparent 7.5%),
  radial-gradient(circle at 6% 45%,rgba(255,47,145,.18) 0 6%,transparent 6.5%),
  radial-gradient(circle at 8% 60%,rgba(255,210,31,.16) 0 5%,transparent 5.5%),
  linear-gradient(135deg,#eaf8ff 0%,#fff 45%,#fff0fa 100%)}
.hero:before{left:-52px;top:100px;width:118px;height:172px;border-radius:55% 55% 50% 50%;background:linear-gradient(145deg,#18b9f4,#0876d8);box-shadow:54px 90px 0 -12px rgba(255,47,145,.72),20px 176px 0 -20px rgba(255,210,31,.76);opacity:.95;transform:rotate(-8deg)}
.hero:after{right:-65px;bottom:-70px;width:210px;height:210px;background:radial-gradient(circle at 35% 35%,#ff78bd 0 22%,#ff2f91 60%,#ff9bd0 100%);opacity:.34}
.hero.hf48-hero-branded:before,.hero.hf48-hero-branded:after{display:none!important}
.hero-in{grid-template-columns:1.14fr .86fr;gap:26px;align-items:center}
.hero-card.hf48-mascot-hero{min-height:430px;display:block;padding:34px 46% 28px 22px;background:transparent;border:0;border-radius:0;box-shadow:none;backdrop-filter:none;overflow:visible}
.hero-card.hf48-mascot-hero:after{display:none}
.hf48-mascot-hero .hf48-mascot-copy{position:relative;z-index:4;max-width:360px}.hf48-mascot-hero .hf48-mascot-copy p{position:relative;z-index:4;font-size:16px}
.hf48-mascot-hero .hf48-mascot-copy h2{font-size:30px;line-height:1.05}
.hf48-hero-mascot-img{position:absolute;right:-5%;bottom:-18px;width:67%;max-height:455px;object-fit:contain;z-index:3;filter:drop-shadow(0 18px 26px rgba(18,35,61,.16))}
.hf48-mascot-hero:before{content:'✦  ✦  •  ✦';position:absolute;right:2%;top:4%;font-size:26px;letter-spacing:12px;color:var(--hf48-pink);text-shadow:34px 34px 0 var(--hf48-yellow),-20px 54px 0 var(--hf48-cyan);z-index:1;opacity:.9}
.hf48-mascot-note{display:inline-flex;align-items:center;gap:7px;margin-top:14px;padding:8px 11px;border-radius:999px;background:linear-gradient(90deg,#e8f8ff,#fff0f7);color:#1769aa;font-size:12px;font-weight:900}
.hf48-gallery-intro{max-width:1320px;margin:0 auto 22px;display:flex;align-items:center;gap:18px;padding:16px 20px;border:1px solid #e6eef7;border-radius:20px;background:linear-gradient(120deg,#eaf9ff,#fff 48%,#fff0f7)}
.hf48-gallery-intro img{width:104px;height:76px;object-fit:contain;flex:0 0 auto}.hf48-gallery-intro strong{display:block;font-size:18px;color:var(--hf48-navy)}.hf48-gallery-intro span{display:block;color:#667c93;font-size:13px;line-height:1.45;margin-top:4px}
.hf48-brand-cta{max-width:1320px;margin:0 auto;padding:0 24px 58px}.hf48-brand-cta-in{display:grid;grid-template-columns:1fr 220px;align-items:center;gap:22px;border-radius:28px;padding:28px 30px;background:linear-gradient(120deg,#e5f8ff,#fff 45%,#fff0f7 75%,#fff8d8);border:1px solid #e0e9f3;overflow:hidden}.hf48-brand-cta h2{margin:4px 0 8px;font-size:30px}.hf48-brand-cta p{margin:0 0 16px;color:#61778f}.hf48-brand-cta img{width:100%;max-height:185px;object-fit:contain}.hf48-brand-cta .cta{display:inline-flex}
@media(max-width:1050px){.grid{grid-template-columns:repeat(3,minmax(0,1fr))}.hf48-category-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.hf48-process-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:900px){.hf48-real-balloons{width:110px;left:-28px;top:94px}.hf48-header-search{display:none}.site-nav{top:87px}.hero-in{grid-template-columns:1fr}.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.hf48-category-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:620px){.preview-bar{font-size:7px!important;line-height:1.15!important;padding:3px 6px!important;letter-spacing:.035em!important}.hf48-real-balloons{display:none}.hf48-topline{font-size:9px;padding:5px 8px}.header-in{padding:8px 12px}.site-nav{top:69px}.hero-in{padding:32px 14px 38px;row-gap:28px}.hero h1{font-size:38px}.hf48-categories{padding:34px 14px}.hf48-section-heading{align-items:flex-start;flex-direction:column}.hf48-section-heading h2{font-size:28px}.hf48-category-grid{grid-template-columns:1fr 1fr;gap:9px}.hf48-category-card{padding:11px;gap:8px}.hf48-cat-icon{width:38px;height:38px;font-size:19px}.hf48-cat-copy strong{font-size:12px}.hf48-cat-copy small{font-size:10px}.main{padding:34px 12px 52px}.grid{grid-template-columns:1fr}.hf48-process{padding:42px 14px}.hf48-process-grid{grid-template-columns:1fr}.photo{aspect-ratio:4/3}.hero-card.hf48-mascot-hero{min-height:455px;padding:26px 16px 245px;margin-top:4px}.hf48-hero-mascot-img{width:82%;right:7%;bottom:6px;max-height:250px}.hf48-mascot-hero .hf48-mascot-copy{max-width:none}.hf48-gallery-intro{margin:0 14px 18px;padding:12px}.hf48-gallery-intro img{width:80px;height:66px}.hf48-brand-cta{padding:0 14px 42px}.hf48-brand-cta-in{grid-template-columns:1fr;padding:22px}.hf48-brand-cta img{max-height:180px;order:-1}}
/* HF51.1 — acabamento profissional: um único cabeçalho azul, sem efeito de banner empilhado */
.header{background:#0b8fdf;border:0;box-shadow:none;overflow:visible}
.header-in{max-width:1320px;padding:8px 24px 6px;gap:24px;min-height:100px;overflow:visible}.brand{gap:0;min-height:84px;overflow:visible;flex:0 0 420px;display:flex;align-items:center}.brand-logo{width:410px;height:84px;object-fit:contain;object-position:left center;display:block;overflow:visible;filter:drop-shadow(0 3px 7px rgba(0,0,0,.12));border-radius:0}.brand-copy{display:none!important}
.hf48-header-search{background:#fff;border:1px solid rgba(255,255,255,.88);box-shadow:0 3px 12px rgba(0,44,92,.10);margin-left:0;max-width:520px}.hf48-header-search input{color:#17324e}.header-actions .cta{box-shadow:0 6px 16px rgba(18,86,48,.20)}
.site-nav{top:100px;background:#0b8fdf;border-top:1px solid rgba(255,255,255,.14);border-bottom:0;box-shadow:0 6px 14px rgba(5,62,117,.10)}.site-nav-in{background:transparent}.site-nav a,.site-nav button{color:#fff}.site-nav a:hover,.site-nav button:hover{background:rgba(255,255,255,.12);color:#fff}
.hf48-topline{background:#0a73c8!important;border:0!important;box-shadow:none!important}
.hf50-carousel{background:transparent;padding:0 24px 24px;margin:0;position:relative;z-index:4}.hf50-carousel-shell{max-width:1480px;margin:auto;position:relative;overflow:hidden;border:1px solid #dbe9f6;border-radius:25px;background:linear-gradient(115deg,#eefaff 0%,#fff 45%,#fff1f8 76%,#fff9df 100%);box-shadow:0 14px 38px rgba(18,35,61,.08);padding:18px 52px 22px}.hf50-carousel-viewport{overflow:hidden;position:relative;z-index:2}.hf50-carousel-track{display:flex;gap:14px;transition:transform .46s cubic-bezier(.2,.75,.25,1);will-change:transform}.hf50-carousel-slide{flex:0 0 calc((100% - 42px)/4);min-width:0;position:relative;border-radius:22px;overflow:hidden;min-height:235px;padding:0;display:flex;flex-direction:column;justify-content:flex-end;background:linear-gradient(135deg,#0875d4,#14b9f4);box-shadow:0 10px 24px rgba(18,35,61,.10);isolation:isolate}.hf50-carousel-slide:nth-child(4n+2){background:linear-gradient(135deg,#6447e8,#ff2f91)}.hf50-carousel-slide:nth-child(4n+3){background:linear-gradient(135deg,#00a9de,#0875d4)}.hf50-carousel-slide:nth-child(4n+4){background:linear-gradient(135deg,#ff2f91,#ff8a33)}.hf50-carousel-media{position:absolute;inset:0;z-index:-2;background:transparent;border:0;border-radius:0;height:auto;box-shadow:none}.hf50-carousel-product-img{width:100%;height:100%;object-fit:cover;padding:0;opacity:.38;filter:saturate(1.08) contrast(1.02)}.hf50-carousel-slide:after{content:'';position:absolute;inset:0;z-index:-1;background:linear-gradient(180deg,rgba(5,25,55,.02) 20%,rgba(5,25,55,.82) 100%)}.hf50-carousel-copy{padding:22px;max-width:none;color:#fff}.hf50-carousel-kicker{display:inline-flex;color:#fff;font-size:10px;font-weight:950;text-transform:uppercase;letter-spacing:.07em;background:rgba(255,255,255,.18);padding:5px 8px;border-radius:999px}.hf50-carousel-copy h2{font-size:24px;line-height:1.05;color:#fff;margin:8px 0 5px;text-shadow:0 2px 8px rgba(0,0,0,.25)}.hf50-carousel-tax{font-size:10px;font-weight:900;color:#fff;text-transform:uppercase;letter-spacing:.04em;opacity:.88}.hf50-carousel-copy p{display:none}.hf50-carousel-actions{display:flex;gap:7px;flex-wrap:wrap;margin-top:10px}.hf50-carousel-actions button{border:0;border-radius:11px;padding:10px 13px;font-size:12px;font-weight:900;cursor:pointer}.hf50-carousel-product{background:#fff;color:#0875d4}.hf50-carousel-whatsapp{background:#25d366;color:#fff}.hf50-carousel-placeholder{font-size:20px;font-weight:950;color:#fff}.hf50-carousel-fox{display:none}.hf50-carousel-arrow{position:absolute;top:50%;transform:translateY(-50%);z-index:6;width:38px;height:38px;border-radius:50%;border:1px solid #cfe2f3;background:rgba(255,255,255,.96);color:#0875d4;font-size:27px;line-height:1;cursor:pointer;box-shadow:0 6px 18px rgba(18,35,61,.12)}.hf50-carousel-arrow.prev{left:8px}.hf50-carousel-arrow.next{right:8px}.hf50-carousel-dots{position:relative;z-index:7;display:flex;justify-content:center;gap:6px;margin-top:14px}.hf50-carousel-dot{width:8px;height:8px;border:0;border-radius:50%;background:#b8cee0;padding:0;cursor:pointer}.hf50-carousel-dot.active{width:23px;border-radius:999px;background:linear-gradient(90deg,#0875d4,#ff2f91)}
@media(max-width:1100px){.brand{flex-basis:340px}.brand-logo{width:332px;height:76px}.header-in{min-height:92px}.site-nav{top:92px}.hf50-carousel-slide{flex-basis:calc((100% - 14px)/2);min-height:220px}}
@media(max-width:900px){.brand{flex-basis:260px}.brand-logo{width:252px;height:64px}.header-in{min-height:78px}.site-nav{top:78px}.hf48-header-search{display:none}.hf50-carousel-slide{flex-basis:calc((100% - 14px)/2);min-height:220px}}
@media(max-width:620px){.hf48-topline{display:none!important}.header{background:#0b8fdf}.header-in{padding:5px 8px 4px;min-height:66px;gap:6px}.brand{flex:1 1 auto;min-width:0;min-height:56px}.brand-logo{width:min(190px,58vw);height:56px;object-fit:contain;object-position:left center}.header-actions{flex:0 0 auto}.header-actions .cta{padding:10px 11px;font-size:11px;white-space:nowrap}.site-nav{top:66px;background:#0b8fdf;border-top:1px solid rgba(255,255,255,.12);box-shadow:0 5px 12px rgba(5,62,117,.10)}.site-nav-in{background:transparent;overflow-x:auto;justify-content:flex-start;padding:0 6px;gap:0}.site-nav a,.site-nav button{font-size:11px;padding:10px 11px;white-space:nowrap}.hf50-carousel{padding:0 10px 20px;margin:0}.hf50-carousel-shell{border-radius:18px;padding:12px 42px 16px}.hf50-carousel-slide{flex-basis:100%;min-height:185px}.hf50-carousel-copy{padding:16px}.hf50-carousel-copy h2{font-size:22px}.hf50-carousel-arrow{width:34px;height:34px}.hf50-carousel-arrow.prev{left:5px}.hf50-carousel-arrow.next{right:5px}}
/* HF51.1 — carrossel fixado exatamente entre o Hero e “Explore por categoria”. */
.hf48-hero-branded + .hf50-carousel{margin-top:0!important;padding-top:0!important}
.hf50-carousel + .hf48-categories{margin-top:0!important}
/* HF51.1 — cabeçalho final aprovado: marca transparente sobre um único azul, sem emendas */
.hf48-topline{display:none!important}
.header{background:linear-gradient(90deg,#0878d7 0%,#079de5 58%,#10b4e8 100%)!important;border:0!important;box-shadow:none!important}
.header-in{max-width:1400px!important;min-height:116px!important;padding:8px 28px!important;gap:28px!important;overflow:visible!important}
.brand{flex:0 0 455px!important;min-height:100px!important;overflow:visible!important;display:flex!important;align-items:center!important}
.brand-logo{width:450px!important;height:104px!important;object-fit:contain!important;object-position:left center!important;background:transparent!important;border:0!important;border-radius:0!important;box-shadow:none!important;filter:drop-shadow(0 3px 6px rgba(0,55,105,.14))!important}
.hf48-header-search{max-width:520px!important;flex:1 1 430px!important}
.site-nav{top:116px!important;background:linear-gradient(90deg,#0878d7 0%,#079de5 58%,#10b4e8 100%)!important;border:0!important;border-top:1px solid rgba(255,255,255,.16)!important;box-shadow:0 6px 14px rgba(5,62,117,.10)!important}
.site-nav-in{max-width:1400px!important;background:transparent!important}
@media(max-width:1100px){.header-in{min-height:100px!important}.brand{flex-basis:360px!important;min-height:88px!important}.brand-logo{width:355px!important;height:88px!important}.site-nav{top:100px!important}}
@media(max-width:900px){.header-in{min-height:84px!important}.brand{flex-basis:280px!important;min-height:74px!important}.brand-logo{width:275px!important;height:74px!important}.site-nav{top:84px!important}}
@media(max-width:620px){.header-in{min-height:74px!important;padding:6px 8px!important;gap:7px!important}.brand{flex:1 1 auto!important;min-width:0!important;min-height:64px!important}.brand-logo{width:min(205px,61vw)!important;height:64px!important;object-fit:contain!important;object-position:left center!important}.header-actions{flex:0 0 auto!important}.header-actions .cta{padding:10px 10px!important;font-size:10px!important}.site-nav{top:74px!important;border-top:1px solid rgba(255,255,255,.15)!important;overflow:visible!important}.site-nav-in{overflow:visible!important;justify-content:flex-start!important;padding:0 5px!important;gap:0!important;position:relative!important}.site-nav a,.site-nav button{font-size:9.7px!important;padding:10px 7px!important;white-space:nowrap!important}.site-nav .hf50-mobile-hide{display:none!important}.hf50-mobile-more{display:block!important;margin-left:auto!important;position:relative!important}.hf50-mobile-more>button{display:flex!important;align-items:center!important;gap:4px!important;color:#fff!important;background:rgba(255,255,255,.09)!important;border:0!important;border-radius:8px!important}.hf50-more-menu{display:none;position:absolute;right:0;top:calc(100% + 5px);min-width:160px;background:#fff;border:1px solid #dce8f3;border-radius:12px;padding:6px;box-shadow:0 12px 30px rgba(10,55,100,.20);z-index:9999}.hf50-more-menu.open{display:grid}.hf50-more-menu a,.hf50-more-menu button{display:block!important;width:100%!important;text-align:left!important;color:#173d66!important;background:#fff!important;border:0!important;border-radius:8px!important;padding:10px 11px!important;font-size:12px!important}.hf50-more-menu a:hover,.hf50-more-menu button:hover{background:#eef7ff!important}}
@media(min-width:621px){.hf50-mobile-more{display:none!important}}


'''
    pagina = pagina.replace("</style>", css + "</style>", 1)

    if mascotes.get("logo_wordmark"):
        pagina = re.sub(
            r'<img\s+class=[\'\"]brand-logo[\'\"]\s+src=[\'\"][^\'\"]*[\'\"]\s+alt=[\'\"][^\'\"]*[\'\"]>',
            f'<img class="brand-logo" src="{mascotes["logo_wordmark"]}" alt="AlphaFest">',
            pagina, count=1, flags=re.S,
        )

    # Faixa comercial discreta no topo.
    pagina = pagina.replace("<body>", '<body><div class="hf48-topline">✨ Personalizados para festas, empresas e presentes · Atendimento direto pelo WhatsApp</div>', 1)

    # Busca principal no cabeçalho. O formulário replica a busca já existente na vitrine.
    search_header = '''<form class="hf48-header-search" id="hf48-header-search"><input id="hf48-header-search-input" type="search" placeholder="O que você está procurando?"><button type="submit">Buscar</button></form>'''
    pagina = pagina.replace('<div class="header-actions">', search_header + '<div class="header-actions">', 1)

    categorias_html = _categorias_html(catalogo)

    # Hero mais comercial: preserva estatísticas e CTAs, só reorganiza a linguagem.
    if mascotes.get("hero"):
        hero_novo = f'''<section class="hero hf48-hero-branded" id="inicio">{f'<img class="hf48-real-balloons" src="{mascotes.get("baloes", "")}" alt="Balões decorativos AlphaFest">' if mascotes.get("baloes") else ""}<div class="hero-in"><div>
          <div class="eyebrow">AlphaFest · Personalizados & Balões</div>
          <h1>Ideias que viram <span>presentes, festas e marcas.</span></h1>
          <p>{html.escape(slogan)} Explore produtos, veja trabalhos reais e peça uma personalização do seu jeito — quantidade, cor, material e prazo combinados com a AlphaFest.</p>
          <div class="hero-actions"><a class="cta" href="#contato">💬 Quero um orçamento</a><a class="secondary" href="#produtos">Ver produtos</a></div>
          <div class="hf48-trust"><span>✓ Sem pedido mínimo</span><span>✓ Personalização sob medida</span><span>✓ Atendimento pelo WhatsApp</span></div>
          </div><aside class="hero-card hf48-mascot-hero"><div class="hf48-mascot-copy"><h2>Uma marca feita para ficar na memória.</h2><p>Produtos, ideias e trabalhos reais com o jeito AlphaFest de transformar cada detalhe em presença.</p><div class="hf48-hero-benefits"><div class="hf48-hero-benefit"><b>💗</b><span>Personalização que conta sua história</span></div><div class="hf48-hero-benefit"><b>⭐</b><span>Qualidade em cada detalhe</span></div><div class="hf48-hero-benefit"><b>🎁</b><span>Ideias para todas as ocasiões</span></div></div><div class="hf48-mascot-note">💙 Thu e Fox dão as boas-vindas</div></div><img class="hf48-hero-mascot-img" src="{mascotes['hero']}" alt="Thu e Fox, mascotes da AlphaFest"></aside></div></section>'''
    else:
        hero_novo = f'''<section class="hero" id="inicio"><div class="hero-in"><div>
          <div class="eyebrow">AlphaFest · Personalizados & Balões</div>
          <h1>Ideias que viram <span>presentes, festas e marcas.</span></h1>
          <p>{html.escape(slogan)} Explore produtos, veja trabalhos reais e peça uma personalização do seu jeito — quantidade, cor, material e prazo combinados com a AlphaFest.</p>
          <div class="hero-actions"><a class="cta" href="#contato">💬 Quero um orçamento</a><a class="secondary" href="#produtos">Ver produtos</a></div>
          <div class="hf48-trust"><span>✓ Sem pedido mínimo</span><span>✓ Personalização sob medida</span><span>✓ Atendimento pelo WhatsApp</span></div>
          </div><aside class="hero-card"><div class="eyebrow">Explore a AlphaFest</div><h2>Encontre uma referência e transforme em algo seu.</h2><p>Use categorias e subcategorias para chegar rápido ao que procura. Na Galeria, veja trabalhos reais já produzidos.</p>
          <div class="hero-stat"><div class="stat"><strong>{total}</strong><span>produtos na vitrine</span></div><div class="stat"><strong>{total_categorias}</strong><span>categorias atuais</span></div></div></aside></div></section>'''

    pagina = re.sub(r"<section\s+class=['\"]hero['\"]\s+id=['\"]inicio['\"]>.*?</section>", hero_novo, pagina, count=1, flags=re.S)

    if categorias_html:
        # Coloca categorias imediatamente após o hero.
        pos = pagina.find('</section>', pagina.find('id="inicio"'))
        if pos >= 0:
            pos += len('</section>')
            pagina = pagina[:pos] + categorias_html + pagina[pos:]

    # HF50.1 — carrossel comercial no espaço entre Hero e Categorias.
    # A seleção vem do mesmo Catálogo: CarrosselSite (preferencial) ou Destaque
    # como fallback visual. Nada é publicado/salvo por esta função.
    carrossel_html = _carrossel_html(catalogo, imagem_resolver=imagem_resolver, mascotes=mascotes)
    if carrossel_html:
        pos = pagina.find('</section>', pagina.find('id="inicio"'))
        if pos >= 0:
            pos += len('</section>')
            pagina = pagina[:pos] + carrossel_html + pagina[pos:]

    if incluir_galeria and mascotes.get("galeria"):
        galeria_intro = f'''<div class="hf48-gallery-intro"><img src="{mascotes['galeria']}" alt="Fox, mascote da AlphaFest"><div><strong>A Fox separou inspirações reais para você.</strong><span>Use Categoria, Subcategoria e Tema para encontrar trabalhos já produzidos e pedir algo parecido pelo WhatsApp.</span></div></div>'''
        marcador_galeria = '<section class="gallery-section" id="galeria">'
        if marcador_galeria in pagina:
            pagina = pagina.replace(marcador_galeria, marcador_galeria + galeria_intro, 1)

    # Processo simples e visual, sem criar novo cadastro ou etapa no Manager.
    processo = '''<section class="hf48-process" id="como-funciona"><div class="hf48-wrap"><div class="hf48-section-heading"><div><span class="hf48-kicker">Simples do começo ao fim</span><h2>Como pedir na AlphaFest</h2><p>Você encontra uma referência no site e a personalização acontece na conversa, sem formulário complicado.</p></div></div><div class="hf48-process-grid">
      <div class="hf48-process-card"><b>1</b><strong>Escolha uma ideia</strong><span>Navegue pelo catálogo ou pela Galeria de trabalhos realizados.</span></div>
      <div class="hf48-process-card"><b>2</b><strong>Fale com a AlphaFest</strong><span>Envie a referência pelo WhatsApp usando o botão do próprio site.</span></div>
      <div class="hf48-process-card"><b>3</b><strong>Defina os detalhes</strong><span>Cor, quantidade, tamanho, material, tema e prazo conforme o projeto.</span></div>
      <div class="hf48-process-card"><b>4</b><strong>Receba seu personalizado</strong><span>A equipe produz o pedido de acordo com o combinado.</span></div>
    </div></div></section>'''
    # Insere antes de Serviços para manter a jornada comercial clara.
    marcador = '<section class="site-section pink" id="servicos">'
    if marcador in pagina:
        pagina = pagina.replace(marcador, processo + marcador, 1)

    if mascotes.get("cta"):
        marca_cta = f'''<section class="hf48-brand-cta"><div class="hf48-brand-cta-in"><div><span class="hf48-kicker">Fale com a AlphaFest</span><h2>Achou uma ideia? Thu e Fox ajudam você a transformar em algo seu.</h2><p>Envie a referência no WhatsApp e conte os detalhes. A equipe orienta material, quantidade, personalização e prazo.</p><a class="cta" href="#contato">💬 Quero pedir um orçamento</a></div><img src="{mascotes['cta']}" alt="Thu e Fox, mascotes da AlphaFest"></div></section>'''
        pagina = pagina.replace('<footer class="footer">', marca_cta + '<footer class="footer">', 1)

    # Adiciona Categorias e Como funciona na navegação gerada pelo site completo.
    pagina = pagina.replace(
        '<button type="button" data-site-scroll="inicio">Início</button><button type="button" data-site-scroll="produtos">Produtos</button>',
        '<button type="button" data-site-scroll="inicio">Início</button><button type="button" data-site-scroll="categorias">Categorias</button><button type="button" data-site-scroll="produtos">Produtos</button>',
        1,
    )
    pagina = pagina.replace(
        '<a href="#inicio">Início</a><a href="#produtos">Produtos</a>',
        '<a href="#inicio">Início</a><a href="#categorias">Categorias</a><a href="#produtos">Produtos</a>',
        1,
    )

    # Identifica a prévia corretamente sem alterar a produção.
    preview_rotulo = 'PRÉVIA INTERNA HF51.1 · CABEÇALHO FINAL TRANSPARENTE + CARROSSEL PROMOCIONAL · NÃO PUBLICADA' if usar_mascotes else 'PRÉVIA INTERNA HF48.1 · NOVO VISUAL COMERCIAL · NÃO PUBLICADA'
    pagina = re.sub(r"<div\s+class=['\"]preview-bar['\"]>.*?</div>", f'<div class="preview-bar">{preview_rotulo}</div>', pagina, count=1, flags=re.S)

    js = r'''
(function(){
  const form=document.getElementById('hf48-header-search');
  const topInput=document.getElementById('hf48-header-search-input');
  const productInput=document.getElementById('search');
  if(form && topInput && productInput){
    form.addEventListener('submit',function(ev){
      ev.preventDefault(); productInput.value=topInput.value || '';
      productInput.dispatchEvent(new Event('input',{bubbles:true}));
      const alvo=document.getElementById('produtos'); if(alvo) alvo.scrollIntoView({behavior:'smooth',block:'start'});
    });
  }
  document.querySelectorAll('[data-hf48-cat]').forEach(function(btn){
    btn.addEventListener('click',function(){
      const slug=btn.getAttribute('data-hf48-cat');
      const filtro=document.querySelector('.category-filter[data-cat="'+slug+'"]');
      if(filtro) filtro.click();
      const alvo=document.getElementById('produtos'); if(alvo) alvo.scrollIntoView({behavior:'smooth',block:'start'});
    });
  });

  // HF51.1 — carrossel em loop infinito real: autoplay sempre avança no mesmo sentido.
  const shell=document.querySelector('.hf50-carousel-shell');
  if(shell){
    const track=shell.querySelector('.hf50-carousel-track');
    const slides=[...shell.querySelectorAll('.hf50-carousel-slide')];
    const dots=[...shell.querySelectorAll('.hf50-carousel-dot')];
    const prev=shell.querySelector('.hf50-carousel-arrow.prev');
    const next=shell.querySelector('.hf50-carousel-arrow.next');
    let idx=0, timer=null, touchStart=null, resetting=false;
    const clones=[];
    if(track&&slides.length){
      slides.forEach((slide)=>{
        const clone=slide.cloneNode(true);
        clone.classList.add('hf50-carousel-clone');
        clone.setAttribute('aria-hidden','true');
        clone.querySelectorAll('[id]').forEach(el=>el.removeAttribute('id'));
        track.appendChild(clone); clones.push(clone);
      });
    }
    function visibleCount(){
      if(!slides.length||!track)return 1;
      const sw=slides[0].getBoundingClientRect().width;
      const tw=track.parentElement.getBoundingClientRect().width;
      return Math.max(1,Math.round(tw/Math.max(1,sw)));
    }
    function stepSize(){
      if(!slides.length||!track)return 0;
      const gap=parseFloat(getComputedStyle(track).gap||'0')||0;
      return slides[0].getBoundingClientRect().width+gap;
    }
    function paint(animate=true){
      if(!slides.length||!track)return;
      track.style.transition=animate?'transform .46s cubic-bezier(.2,.75,.25,1)':'none';
      track.style.transform='translateX(-'+(idx*stepSize())+'px)';
      const logical=((idx%slides.length)+slides.length)%slides.length;
      const vis=visibleCount();
      slides.forEach((s,i)=>s.setAttribute('aria-hidden',(i>=logical&&i<logical+vis)?'false':'true'));
      clones.forEach(c=>c.setAttribute('aria-hidden','true'));
      dots.forEach((d,i)=>{d.style.display='block';d.classList.toggle('active',i===logical);});
    }
    function forward(){
      if(!slides.length||resetting)return;
      idx+=1; paint(true);
    }
    function backward(){
      if(!slides.length||resetting)return;
      if(idx===0){
        resetting=true; idx=slides.length; paint(false);
        requestAnimationFrame(()=>requestAnimationFrame(()=>{resetting=false;idx-=1;paint(true);}));
      }else{idx-=1;paint(true);}
    }
    function jumpTo(n){
      if(!slides.length)return;
      idx=Math.max(0,Math.min(slides.length-1,n)); paint(true);
    }
    function stop(){if(timer){clearInterval(timer);timer=null;}}
    function start(){stop(); if(slides.length>visibleCount()) timer=setInterval(forward,5200);}
    if(track)track.addEventListener('transitionend',()=>{
      if(idx>=slides.length){
        resetting=true; idx=0; paint(false);
        requestAnimationFrame(()=>{resetting=false;});
      }
    });
    if(prev)prev.addEventListener('click',()=>{backward();start();});
    if(next)next.addEventListener('click',()=>{forward();start();});
    dots.forEach((d,i)=>d.addEventListener('click',()=>{jumpTo(i);start();}));
    shell.addEventListener('mouseenter',stop); shell.addEventListener('mouseleave',start);
    shell.addEventListener('focusin',stop); shell.addEventListener('focusout',start);
    shell.addEventListener('touchstart',e=>{touchStart=e.changedTouches&&e.changedTouches[0]?e.changedTouches[0].clientX:null;},{passive:true});
    shell.addEventListener('touchend',e=>{
      if(touchStart===null)return; const end=e.changedTouches&&e.changedTouches[0]?e.changedTouches[0].clientX:touchStart;
      const delta=end-touchStart; touchStart=null; if(Math.abs(delta)>42){delta<0?forward():backward();start();}
    },{passive:true});
    window.addEventListener('resize',()=>{paint(false);start();});
    paint(false); start();
  }

  // HF51.1 — menu mobile enxuto: 4 destinos principais + “Mais”.
  const mobileNav=document.querySelector('.site-nav-in');
  if(mobileNav && !mobileNav.querySelector('.hf50-mobile-more')){
    const hiddenLabels=new Set(['Serviços','Quem Somos','Contato']);
    const originals=[...mobileNav.children].filter(function(el){return el.matches && el.matches('a,button');});
    const moreWrap=document.createElement('div'); moreWrap.className='hf50-mobile-more';
    const moreBtn=document.createElement('button'); moreBtn.type='button'; moreBtn.setAttribute('aria-expanded','false'); moreBtn.innerHTML='☰ <span>Mais</span>';
    const menu=document.createElement('div'); menu.className='hf50-more-menu';
    originals.forEach(function(el){
      const label=(el.textContent||'').trim();
      if(hiddenLabels.has(label)){
        el.classList.add('hf50-mobile-hide');
        const clone=el.cloneNode(true); clone.classList.remove('hf50-mobile-hide');
        clone.addEventListener('click',function(ev){
          if(el.tagName==='BUTTON'){
            ev.preventDefault(); el.click();
          }
          menu.classList.remove('open'); moreBtn.setAttribute('aria-expanded','false');
        });
        menu.appendChild(clone);
      }
    });
    if(menu.children.length){
      moreBtn.addEventListener('click',function(ev){ev.stopPropagation();const open=menu.classList.toggle('open');moreBtn.setAttribute('aria-expanded',open?'true':'false');});
      moreWrap.appendChild(moreBtn); moreWrap.appendChild(menu); mobileNav.appendChild(moreWrap);
      document.addEventListener('click',function(ev){if(!moreWrap.contains(ev.target)){menu.classList.remove('open');moreBtn.setAttribute('aria-expanded','false');}});
      window.addEventListener('resize',function(){if(window.innerWidth>620){menu.classList.remove('open');moreBtn.setAttribute('aria-expanded','false');}});
    }
  }

  document.querySelectorAll('.hf50-carousel-product').forEach(function(btn){
    btn.addEventListener('click',function(){
      const nome=btn.getAttribute('data-hf50-product')||'';
      const back=document.getElementById('taxonomy-back');
      if(back && back.offsetParent!==null) back.click();
      if(productInput){productInput.value=nome; productInput.dispatchEvent(new Event('input',{bubbles:true}));}
      if(topInput) topInput.value=nome;
      const alvo=document.getElementById('produtos'); if(alvo) alvo.scrollIntoView({behavior:'smooth',block:'start'});
    });
  });
})();
'''
    pagina = pagina.replace("</body>", "<script>" + js + "</script></body>", 1)
    return pagina
