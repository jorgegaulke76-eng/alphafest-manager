"""HF48.1 — camada visual comercial do site AlphaFest.

Aplica somente apresentação/UX sobre o HTML já gerado pelos serviços HF40-HF47.
Não altera Catálogo, Galeria, publicação Cloudflare, dados ou Fonte Única.
O recurso é opt-in e usado inicialmente apenas em prévia interna.
"""
from __future__ import annotations

import html
import re
from typing import Any, Dict, Iterable, List

from site_vitrine_service import resumir_vitrine


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

    css = r'''
/* HF48.1 — nova linguagem visual comercial (somente opt-in) */
:root{--hf48-navy:#12233d;--hf48-blue:#0876d8;--hf48-sky:#eaf7ff;--hf48-pink:#ff4f91;--hf48-yellow:#ffd84d;--hf48-bg:#f7f9fc;--hf48-border:#e3e9f1}
body{background:var(--hf48-bg)}
.hf48-topline{background:var(--hf48-navy);color:#fff;text-align:center;padding:8px 16px;font-size:12px;font-weight:800;letter-spacing:.01em}
.header{position:sticky;top:0;background:#fff;border-bottom:1px solid var(--hf48-border);box-shadow:0 4px 18px rgba(18,35,61,.05)}
.header-in{max-width:1320px;padding:14px 24px}.brand-logo{width:74px;height:58px}.brand-copy strong{font-size:18px}.brand-copy span{font-size:12px}
.hf48-header-search{flex:1;max-width:610px;margin-left:22px;display:flex;align-items:center;border:1px solid #d9e3ee;border-radius:15px;background:#f8fbfe;overflow:hidden;min-height:48px}
.hf48-header-search input{flex:1;border:0;outline:0;background:transparent;padding:0 16px;font-size:14px;color:var(--ink)}.hf48-header-search button{border:0;background:var(--hf48-blue);color:#fff;font-weight:900;align-self:stretch;padding:0 20px;cursor:pointer}
.header-actions .ghost{display:none}.header-actions .cta{border-radius:14px;padding:13px 18px}
.site-nav{top:87px;background:#fff;border-bottom:1px solid var(--hf48-border)}.site-nav-in{max-width:1320px;justify-content:flex-start;padding:0 24px}.site-nav a,.site-nav button{font-size:13px;padding:13px 14px}.site-nav a:hover,.site-nav button:hover{background:#eef7ff}
.hero{background:linear-gradient(135deg,#edf8ff 0%,#fff 48%,#fff0f7 100%);border-bottom:0}.hero-in{max-width:1320px;padding:64px 24px 58px;grid-template-columns:1.08fr .92fr;gap:46px}.hero h1{font-size:clamp(42px,5.6vw,76px);line-height:.98}.hero p{max-width:650px}.hero-card{border:0;border-radius:28px;background:#fff;box-shadow:0 28px 70px rgba(18,35,61,.13);padding:30px;position:relative;overflow:hidden}.hero-card:after{content:'';position:absolute;width:160px;height:160px;border-radius:50%;background:linear-gradient(135deg,rgba(8,118,216,.13),rgba(255,79,145,.14));right:-42px;top:-48px}.hero-card h2{font-size:28px;margin:8px 0 10px}.hero-stat{position:relative;z-index:2}.stat{background:#f4f9fe;border:1px solid #e8f0f7}.stat strong{font-size:32px}.secondary{border-color:#d8e3ee;border-radius:13px}
.hf48-trust{display:flex;gap:8px;flex-wrap:wrap;margin-top:20px}.hf48-trust span{background:rgba(255,255,255,.82);border:1px solid #dce8f3;border-radius:999px;padding:8px 11px;font-size:12px;font-weight:800;color:#526a83}
.hf48-wrap{max-width:1320px;margin:auto}.hf48-categories{background:#fff;padding:48px 24px}.hf48-section-heading{display:flex;align-items:end;justify-content:space-between;gap:24px;margin-bottom:22px}.hf48-section-heading h2{font-size:34px;margin:4px 0 6px}.hf48-section-heading p{margin:0;color:#657a92}.hf48-kicker{color:var(--hf48-blue);font-size:12px;font-weight:950;text-transform:uppercase;letter-spacing:.09em}.hf48-text-link{border:0;background:transparent;color:var(--hf48-blue);font-weight:900;cursor:pointer;white-space:nowrap}.hf48-category-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.hf48-category-card{border:1px solid var(--hf48-border);background:#fff;border-radius:18px;padding:16px;display:flex;align-items:center;gap:12px;text-align:left;cursor:pointer;transition:.18s;box-shadow:0 6px 20px rgba(18,35,61,.035)}.hf48-category-card:hover{transform:translateY(-2px);border-color:#afd7f8;box-shadow:0 12px 28px rgba(18,35,61,.08)}.hf48-cat-icon{width:46px;height:46px;border-radius:14px;background:#edf8ff;display:flex;align-items:center;justify-content:center;font-size:23px}.hf48-cat-copy{min-width:0;flex:1}.hf48-cat-copy strong{display:block;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.hf48-cat-copy small{display:block;margin-top:4px;color:#75889e}.hf48-cat-arrow{font-size:24px;color:#9db1c5}
.main{max-width:1320px;padding:48px 24px 76px}.section-head{margin-top:0}.section-head h2{font-size:34px}.toolbar{background:#fff;border:1px solid var(--hf48-border);padding:10px;border-radius:18px;box-shadow:0 8px 26px rgba(18,35,61,.04)}.search input{border:0;background:#f8fbfd;border-radius:12px}.taxonomy-step{border-color:var(--hf48-border);box-shadow:0 6px 20px rgba(18,35,61,.025)}
.grid{grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}.product-card{border-color:var(--hf48-border);border-radius:18px;box-shadow:0 8px 24px rgba(18,35,61,.055)}.product-card:hover{box-shadow:0 16px 32px rgba(18,35,61,.105)}.photo{aspect-ratio:1/1}.card-body{padding:15px}.card-body h3{font-size:17px}.card-body p{font-size:13px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}.cta.small{border-radius:11px}
.site-section{padding-top:64px;padding-bottom:64px}.site-section.alt,.site-section.pink{background:#fff}.services-grid{gap:12px}.service-card{box-shadow:0 7px 22px rgba(18,35,61,.045);border-color:var(--hf48-border)}
.hf48-process{background:linear-gradient(120deg,#12233d,#173b67);color:#fff;padding:58px 24px}.hf48-process .hf48-section-heading h2,.hf48-process .hf48-section-heading p{color:#fff}.hf48-process-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.hf48-process-card{border:1px solid rgba(255,255,255,.14);background:rgba(255,255,255,.075);border-radius:18px;padding:20px}.hf48-process-card b{display:flex;width:34px;height:34px;border-radius:50%;align-items:center;justify-content:center;background:#fff;color:#173b67;margin-bottom:12px}.hf48-process-card strong{display:block;font-size:16px}.hf48-process-card span{display:block;margin-top:7px;color:#c9d8e8;font-size:13px;line-height:1.5}
.gallery-section{background:#fff!important}
.footer{background:#0d1c31}.footer-in{max-width:1320px;padding:40px 24px}
@media(max-width:1050px){.grid{grid-template-columns:repeat(3,minmax(0,1fr))}.hf48-category-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.hf48-process-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:900px){.hf48-header-search{display:none}.site-nav{top:87px}.hero-in{grid-template-columns:1fr}.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.hf48-category-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:620px){.hf48-topline{font-size:10px}.header-in{padding:8px 12px}.site-nav{top:69px}.hero-in{padding:36px 14px 32px}.hero h1{font-size:38px}.hf48-categories{padding:34px 14px}.hf48-section-heading{align-items:flex-start;flex-direction:column}.hf48-section-heading h2{font-size:28px}.hf48-category-grid{grid-template-columns:1fr 1fr;gap:9px}.hf48-category-card{padding:11px;gap:8px}.hf48-cat-icon{width:38px;height:38px;font-size:19px}.hf48-cat-copy strong{font-size:12px}.hf48-cat-copy small{font-size:10px}.main{padding:34px 12px 52px}.grid{grid-template-columns:1fr}.hf48-process{padding:42px 14px}.hf48-process-grid{grid-template-columns:1fr}.photo{aspect-ratio:4/3}}
'''
    pagina = pagina.replace("</style>", css + "</style>", 1)

    # Faixa comercial discreta no topo.
    pagina = pagina.replace("<body>", '<body><div class="hf48-topline">✨ Personalizados para festas, empresas e presentes · Atendimento direto pelo WhatsApp</div>', 1)

    # Busca principal no cabeçalho. O formulário replica a busca já existente na vitrine.
    search_header = '''<form class="hf48-header-search" id="hf48-header-search"><input id="hf48-header-search-input" type="search" placeholder="O que você está procurando?"><button type="submit">Buscar</button></form>'''
    pagina = pagina.replace('<div class="header-actions">', search_header + '<div class="header-actions">', 1)

    categorias_html = _categorias_html(catalogo)

    # Hero mais comercial: preserva estatísticas e CTAs, só reorganiza a linguagem.
    hero_novo = f'''<section class="hero" id="inicio"><div class="hero-in"><div>
      <div class="eyebrow">AlphaFest · Personalizados & Balões</div>
      <h1>Ideias que viram <span>presentes, festas e marcas.</span></h1>
      <p>{html.escape(slogan)} Explore produtos, veja trabalhos reais e peça uma personalização do seu jeito — quantidade, cor, material e prazo combinados com a AlphaFest.</p>
      <div class="hero-actions"><a class="cta" href="#contato">💬 Quero um orçamento</a><a class="secondary" href="#produtos">Ver produtos</a></div>
      <div class="hf48-trust"><span>✓ Sem pedido mínimo</span><span>✓ Personalização sob medida</span><span>✓ Atendimento pelo WhatsApp</span></div>
      </div><aside class="hero-card"><div class="eyebrow">Explore a AlphaFest</div><h2>Encontre uma referência e transforme em algo seu.</h2><p>Use categorias e subcategorias para chegar rápido ao que procura. Na Galeria, veja trabalhos reais já produzidos.</p>
      <div class="hero-stat"><div class="stat"><strong>{total}</strong><span>produtos na vitrine</span></div><div class="stat"><strong>{total_categorias}</strong><span>categorias atuais</span></div></div></aside></div></section>'''
    pagina = re.sub(r'<section class="hero" id="inicio">.*?</section>', hero_novo, pagina, count=1, flags=re.S)

    if categorias_html:
        # Coloca categorias imediatamente após o hero.
        pos = pagina.find('</section>', pagina.find('id="inicio"'))
        if pos >= 0:
            pos += len('</section>')
            pagina = pagina[:pos] + categorias_html + pagina[pos:]

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
    pagina = re.sub(r'<div class="preview-bar">.*?</div>', '<div class="preview-bar">PRÉVIA INTERNA HF48.1 · NOVO VISUAL COMERCIAL · NÃO PUBLICADA</div>', pagina, count=1, flags=re.S)

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
})();
'''
    pagina = pagina.replace("</body>", "<script>" + js + "</script></body>", 1)
    return pagina
