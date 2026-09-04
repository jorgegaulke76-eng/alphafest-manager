"""Site institucional + vitrine AlphaFest (HF40).

A HF40 mantém a vitrine homologada como núcleo comercial e acrescenta as
seções Início, Produtos, Serviços, Quem Somos e Contato usando a mesma
identidade visual. O Catálogo continua sendo a Fonte Única dos produtos e os
dados de contato vêm da configuração oficial da empresa no Manager.

Este módulo é somente leitura: não persiste dados, não publica e não altera DNS.
"""
from __future__ import annotations

import html
import re
from typing import Any, Callable, Dict, Iterable, Optional
from urllib.parse import quote

from site_vitrine_service import gerar_html_vitrine

ImagemResolver = Optional[Callable[[str], str]]


SERVICOS_PADRAO = (
    ("🎉", "Personalizados para festas", "Topos, lembranças, papelaria, displays e peças criadas para cada tema e ocasião."),
    ("🎈", "Balões & decoração", "Balões personalizados, bubbles e soluções decorativas para presentes, festas e eventos."),
    ("🖨️", "Gráfica rápida", "Impressos, banners, faixas, adesivos e materiais gráficos para festas, negócios e eventos."),
    ("🎁", "Brindes personalizados", "Canecas, copos, lembranças e brindes para empresas, equipes, escolas e comemorações."),
    ("💌", "Convites & papelaria", "Convites e papelaria personalizada para aniversários, casamentos, batizados e eventos especiais."),
    ("🧊", "Impressão 3D", "Peças, displays, lembranças e projetos personalizados produzidos sob medida em impressão 3D."),
    ("✨", "Gravação a laser", "Personalização e gravação de peças e brindes com acabamento preciso para projetos especiais."),
    ("🎂", "Kits & composição de festa", "Itens coordenados para montar uma identidade visual completa, do bolo às lembranças."),
)


def _numero_whatsapp(empresa: Dict[str, Any]) -> str:
    numero = re.sub(r"\D", "", str((empresa or {}).get("whatsapp_catalogo") or (empresa or {}).get("celular") or ""))
    if numero and not numero.startswith("55"):
        numero = "55" + numero
    return numero


def _wa(numero: str, mensagem: str) -> str:
    return f"https://wa.me/{numero}?text={quote(mensagem)}" if numero else "#"


def _bloco_servicos() -> str:
    cards = []
    for icone, titulo, texto in SERVICOS_PADRAO:
        cards.append(
            f'''<article class="service-card"><div class="service-icon">{html.escape(icone)}</div>
            <h3>{html.escape(titulo)}</h3><p>{html.escape(texto)}</p></article>'''
        )
    return "".join(cards)


def gerar_html_site_completo(
    catalogo: Iterable[Dict[str, Any]],
    empresa: Dict[str, Any],
    *,
    logo_src: str = "",
    imagem_resolver: ImagemResolver = None,
    modo_preview: bool = True,
    usar_taxonomia_catalogo: bool = False,
) -> str:
    """Gera o site completo sem publicar ou persistir qualquer dado.

    HF45.4 permite uma prévia paralela usando Categoria → Subcategoria do
    Catálogo Oficial. O parâmetro padrão permanece False para preservar o site
    público HF44 até a classificação ser revisada e homologada.
    """
    pagina = gerar_html_vitrine(
        catalogo,
        empresa,
        logo_src=logo_src,
        imagem_resolver=imagem_resolver,
        modo_preview=False,
        usar_taxonomia_catalogo=usar_taxonomia_catalogo,
    )

    empresa = dict(empresa or {})
    nome = str(empresa.get("nome") or "AlphaFest").strip() or "AlphaFest"
    subtitulo = str(empresa.get("subtitulo") or "Personalizados & Balões").strip()
    slogan = str(empresa.get("slogan") or "O poder de estar presente em cada presente!").strip()
    endereco = str(empresa.get("endereco") or "").strip()
    cep = str(empresa.get("cep") or "").strip()
    email = str(empresa.get("email") or "").strip()
    celular = str(empresa.get("celular") or "").strip()
    cidade = str(empresa.get("cidade") or "").strip()
    uf = str(empresa.get("uf") or "").strip()
    numero = _numero_whatsapp(empresa)
    whatsapp = _wa(numero, "Olá! Vim pelo novo site da AlphaFest e gostaria de conversar sobre um projeto personalizado.")
    mapa = "https://www.google.com/maps/search/?api=1&query=" + quote(endereco) if endereco else "#"

    css_extra = r'''
.site-nav{position:sticky;top:79px;z-index:19;background:rgba(255,255,255,.96);backdrop-filter:blur(12px);border-bottom:1px solid var(--line)}
.site-nav-in{max-width:1240px;margin:auto;padding:0 22px;display:flex;align-items:center;justify-content:center;gap:6px;overflow-x:auto;scrollbar-width:none}.site-nav-in::-webkit-scrollbar{display:none}
.site-nav a{color:var(--ink);text-decoration:none;font-size:13px;font-weight:850;padding:11px 13px;border-radius:10px;white-space:nowrap}.site-nav a:hover{background:#eef7ff;color:var(--blue)}
.site-section{padding:72px 22px}.site-section.alt{background:linear-gradient(180deg,#fbfdff,#f6fbff)}.site-section.pink{background:linear-gradient(135deg,#fff,#fff6fb)}
.site-wrap{max-width:1240px;margin:auto}.section-kicker{color:var(--blue);font-size:12px;font-weight:950;letter-spacing:.08em;text-transform:uppercase}.section-title{font-size:38px;line-height:1.08;margin:8px 0 12px}.section-copy{max-width:780px;color:#5d718b;font-size:16px;line-height:1.7;margin:0}
.services-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:28px}.service-card{border:1px solid var(--line);border-radius:18px;background:#fff;padding:22px;box-shadow:0 8px 26px rgba(20,37,61,.05)}.service-icon{font-size:26px}.service-card h3{font-size:17px;margin:12px 0 8px}.service-card p{font-size:14px;line-height:1.55;color:#62758e;margin:0}
.about-grid{display:grid;grid-template-columns:1.12fr .88fr;gap:28px;align-items:stretch}.about-card{border:1px solid var(--line);background:#fff;border-radius:22px;padding:28px;box-shadow:0 12px 34px rgba(20,37,61,.06)}.about-card h3{margin:0 0 14px;font-size:23px}.about-card p{color:#5d718b;line-height:1.75}.about-points{display:grid;gap:12px;margin-top:20px}.about-point{display:flex;gap:10px;align-items:flex-start;background:#f7fbff;border-radius:13px;padding:13px}.about-point strong{display:block;font-size:14px}.about-point span{font-size:13px;color:#647991}
.contact-grid{display:grid;grid-template-columns:1.05fr .95fr;gap:22px;margin-top:28px}.contact-card{border:1px solid var(--line);background:#fff;border-radius:20px;padding:24px}.contact-list{display:grid;gap:12px;margin-top:18px}.contact-item{display:flex;gap:12px;align-items:flex-start}.contact-item b{display:block}.contact-item span,.contact-item a{font-size:14px;color:#60748e;text-decoration:none}.contact-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px}.contact-actions .secondary{display:inline-flex}
.site-footnote{font-size:12px;color:#71849c;margin-top:18px}.legacy-note{margin-top:22px;border:1px dashed #bdd6ea;border-radius:14px;padding:14px;background:#f8fcff;color:#5b7089;font-size:13px}
@media(max-width:940px){.services-grid{grid-template-columns:repeat(2,1fr)}.about-grid,.contact-grid{grid-template-columns:1fr}.site-nav{top:69px}}
@media(max-width:620px){.site-nav{top:69px}.site-nav-in{justify-content:flex-start;padding:0 10px}.site-nav a{padding:10px 9px;font-size:12px}.site-section{padding:46px 14px}.section-title{font-size:30px}.services-grid{grid-template-columns:1fr}.service-card{padding:18px}.about-card,.contact-card{padding:20px}.contact-actions>a{width:100%}}
'''
    pagina = pagina.replace("</style>", css_extra + "</style>", 1)

    # A barra identifica claramente qual estrutura está sendo homologada.
    if modo_preview:
        preview = (
            '<div class="preview-bar">PRÉVIA INTERNA HF45.4 · CATEGORIA → SUBCATEGORIA · NÃO PUBLICADA</div>'
            if usar_taxonomia_catalogo
            else '<div class="preview-bar">PRÉVIA INTERNA HF40 · SITE COMPLETO · AINDA NÃO PUBLICADO</div>'
        )
        pagina = pagina.replace("<body>", "<body>" + preview, 1)

    # Navegação única, mantendo o header da vitrine homologada.
    nav = '''<nav class="site-nav" aria-label="Navegação principal"><div class="site-nav-in">
      <a href="#inicio">Início</a><a href="#produtos">Produtos</a><a href="#servicos">Serviços</a><a href="#quem-somos">Quem Somos</a><a href="#contato">Contato</a>
    </div></nav>'''
    marcador_header = "</header>"
    pagina = pagina.replace(marcador_header, marcador_header + nav, 1)

    local_txt = " · ".join([x for x in [cidade, uf] if x])
    sobre = f'''<section class="site-section alt" id="quem-somos"><div class="site-wrap"><div class="about-grid">
      <div><div class="section-kicker">Quem Somos</div><h2 class="section-title">Personalização com cuidado em cada detalhe.</h2>
      <p class="section-copy">A {html.escape(nome)} é especializada em personalizados para festas, eventos, marcas e presentes. Cada projeto nasce a partir do que o cliente precisa — tema, medida, cor, material, quantidade e prazo — para transformar uma ideia em algo realmente único.</p>
      {('<div class="legacy-note">Esta apresentação reaproveita a essência institucional do site anterior, mas foi reescrita para o novo site. Produtos e dados de contato continuam vindo do Manager.</div>' if modo_preview else '')}</div>
      <aside class="about-card"><h3>Por que falar com a AlphaFest?</h3><div class="about-points">
        <div class="about-point"><div>🎨</div><div><strong>Personalização de verdade</strong><span>Cada pedido pode ser ajustado à ocasião e à identidade do cliente.</span></div></div>
        <div class="about-point"><div>🧩</div><div><strong>Várias soluções no mesmo lugar</strong><span>Personalizados, gráfica, brindes, balões, impressão 3D e gravação a laser.</span></div></div>
        <div class="about-point"><div>💬</div><div><strong>Atendimento direto</strong><span>O orçamento começa pelo WhatsApp e segue de acordo com as escolhas do projeto.</span></div></div>
        <div class="about-point"><div>📍</div><div><strong>AlphaFest em {html.escape(local_txt or 'Itatiba')}</strong><span>{html.escape(slogan)}</span></div></div>
      </div></aside></div></div></section>'''

    servicos = f'''<section class="site-section pink" id="servicos"><div class="site-wrap"><div class="section-kicker">Serviços</div>
      <h2 class="section-title">Do detalhe da festa à presença da sua marca.</h2>
      <p class="section-copy">O novo site reúne os principais tipos de trabalho da AlphaFest em uma navegação simples. A vitrine mostra exemplos; para medidas, materiais, quantidades e personalizações, o orçamento continua sendo feito sob medida.</p>
      <div class="services-grid">{_bloco_servicos()}</div></div></section>'''

    contact_parts = []
    if celular:
        contact_parts.append(f'<div class="contact-item"><div>💬</div><div><b>WhatsApp</b><a href="{html.escape(whatsapp, quote=True)}" target="_blank" rel="noopener">{html.escape(celular)}</a></div></div>')
    if email:
        contact_parts.append(f'<div class="contact-item"><div>✉️</div><div><b>E-mail</b><a href="mailto:{html.escape(email, quote=True)}">{html.escape(email)}</a></div></div>')
    if endereco:
        endereco_completo = endereco + (f" · CEP {cep}" if cep else "")
        contact_parts.append(f'<div class="contact-item"><div>📍</div><div><b>Endereço</b><span>{html.escape(endereco_completo)}</span></div></div>')

    contato = f'''<section class="site-section" id="contato"><div class="site-wrap"><div class="section-kicker">Contato</div><h2 class="section-title">Conte o que você precisa. A gente monta com você.</h2>
      <p class="section-copy">Como tamanho, quantidade, material, cor e personalização mudam de projeto para projeto, o melhor caminho é conversar diretamente com a AlphaFest.</p>
      <div class="contact-grid"><div class="contact-card"><h3>Fale com a AlphaFest</h3><div class="contact-list">{''.join(contact_parts) or '<div class="contact-item"><div>💬</div><div><b>Contato</b><span>Consulte os canais oficiais da AlphaFest.</span></div></div>'}</div>
      <div class="contact-actions"><a class="cta" href="{html.escape(whatsapp, quote=True)}" target="_blank" rel="noopener">💬 Pedir orçamento</a>{f'<a class="secondary" href="{html.escape(mapa, quote=True)}" target="_blank" rel="noopener">📍 Ver localização</a>' if endereco else ''}</div></div>
      <div class="contact-card"><h3>Como funciona o orçamento</h3><div class="about-points">
        <div class="about-point"><div>1️⃣</div><div><strong>Escolha uma referência</strong><span>Use a vitrine ou descreva sua ideia.</span></div></div>
        <div class="about-point"><div>2️⃣</div><div><strong>Defina os detalhes</strong><span>Tamanho, cor, quantidade, material, personalização e prazo.</span></div></div>
        <div class="about-point"><div>3️⃣</div><div><strong>Receba a orientação</strong><span>A AlphaFest confirma possibilidades, valor e próximos passos.</span></div></div>
      </div></div></div>{('<div class="site-footnote">Dados de contato exibidos nesta página são lidos da configuração oficial da empresa no AlphaFest Manager.</div>' if modo_preview else '')}</div></section>'''

    # A ordem desejada é Início -> Produtos -> Serviços -> Quem Somos -> Contato.
    marcador_mobile = '<a class="mobile-whatsapp"'
    pos = pagina.find(marcador_mobile)
    if pos >= 0:
        pagina = pagina[:pos] + servicos + sobre + contato + pagina[pos:]
    else:
        pagina = pagina.replace("<footer class=\"footer\">", servicos + sobre + contato + '<footer class="footer">', 1)

    # No site completo, o CTA de navegação deixa de falar só em "Ver produtos".
    pagina = pagina.replace('>Ver produtos</a>', '>Produtos</a>', 1)
    return pagina
