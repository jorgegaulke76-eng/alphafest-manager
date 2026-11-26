"""Conteúdo informativo original e permanente para a vitrine AlphaFest.

Sem anúncios, dados pessoais, integrações externas ou ações automáticas.
A seção complementa os produtos e não substitui as Dicas & Inspirações.
"""
from __future__ import annotations

import html

PERGUNTAS = (
    (
        "O que informar ao pedir um personalizado?",
        "Comece pela ocasião e pela data em que o produto será usado. Informe quantidade, "
        "medidas aproximadas, nome ou frase a imprimir e referências de cores ou tema. "
        "Se houver uma identidade visual, envie a arte disponível. Essas informações "
        "permitem avaliar materiais e acabamento antes de elaborar o orçamento.",
    ),
    (
        "Qual a diferença entre arte digital e produto físico?",
        "Uma arte digital é um arquivo destinado a envio ou impressão, enquanto o "
        "produto físico envolve escolha de material, fabricação e eventual montagem. "
        "Ao solicitar convites, tags, topos ou lembranças, esclareça se precisa apenas "
        "do arquivo ou das peças prontas. Formato, dimensões e finalidade mudam a preparação.",
    ),
    (
        "Como escolher balões para um evento?",
        "Considere o local, as dimensões do espaço e a duração prevista. Um arco "
        "tradicional costuma criar um desenho regular; o desconstruído combina "
        "balões de tamanhos diferentes. Para áreas externas, informe exposição ao "
        "sol, vento e pontos de fixação. O tipo de instalação deve considerar a segurança.",
    ),
    (
        "Como conferir nomes, datas e estampas antes da produção?",
        "Revise cada nome, idade, data, telefone e frase exatamente como deverá aparecer. "
        "Confira também a orientação da arte, as cores previstas e a legibilidade "
        "em peças pequenas. Quando houver uma prévia para aprovação, compare todos "
        "os dados com a lista original antes de autorizar a confecção.",
    ),
    (
        "O que considerar ao encomendar brindes para empresas?",
        "Defina quem receberá o brinde, como ele será usado e a quantidade necessária. "
        "Uma marca legível e um objeto útil ajudam a prolongar a lembrança. "
        "Para canecas, ecobags, camisetas e outros materiais, informe a aplicação "
        "pretendida, a arte da marca e o prazo do evento para avaliar possibilidades.",
    ),
    (
        "Como se preparar para um orçamento de impressão 3D?",
        "Explique a função da peça e, sempre que possível, envie medidas ou um desenho "
        "de referência. Informe se ela será decorativa ou funcional, se precisará "
        "encaixar em outra peça e quais condições de uso são esperadas. "
        "A viabilidade depende da geometria, do material e do acabamento pretendido.",
    ),
)

def inject_conteudo_util(site_html: str) -> str:
    """Acrescenta FAQ estático, idempotente, antes do rodapé do site."""
    pagina = str(site_html or "")
    if 'id="guia-personalizacao-alphafest"' in pagina:
        return pagina
    if '<footer class="footer"' not in pagina:
        return pagina

    itens = "".join(
        '<details class="af-guia-item"><summary>' + html.escape(titulo) + '</summary>'
        '<p>' + html.escape(resposta) + '</p></details>'
        for titulo, resposta in PERGUNTAS
    )
    bloco = (
        '<section id="guia-personalizacao-alphafest" class="af-guia" '
        'aria-labelledby="af-guia-title">'
        '<div class="af-guia-inner"><p class="af-guia-kicker">Guia prático AlphaFest</p>'
        '<h2 id="af-guia-title">Antes de encomendar: respostas que ajudam você a escolher</h2>'
        '<p class="af-guia-intro">Informações para planejar personalizados, decoração, '
        'brindes e peças 3D com mais clareza. Cada projeto é avaliado conforme suas '
        'necessidades, materiais e prazo.</p>'
        '<div class="af-guia-list">' + itens + '</div></div></section>'
    )
    style = """<style id="af-guia-style">
.af-guia{padding:48px 18px;background:#f5faff;color:#193c5c}
.af-guia-inner{max-width:980px;margin:0 auto}
.af-guia-kicker{font-size:.82rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#14699a}
.af-guia h2{font-size:clamp(1.5rem,3vw,2.2rem);line-height:1.24;margin:8px 0 12px}
.af-guia-intro{max-width:760px;line-height:1.65;margin:0 0 22px}
.af-guia-list{display:grid;gap:10px}
.af-guia-item{border:1px solid #d9e7f1;background:#fff;border-radius:12px;padding:4px 18px}
.af-guia-item summary{cursor:pointer;font-weight:750;padding:14px 0;line-height:1.5}
.af-guia-item summary:focus-visible{outline:3px solid #1479b8;outline-offset:3px}
.af-guia-item p{margin:0 0 16px;line-height:1.75;color:#34536b}
@media(max-width:620px){.af-guia{padding:32px 14px}.af-guia-item{padding:3px 12px}}
</style>"""
    if "</head>" in pagina:
        pagina = pagina.replace("</head>", style + "</head>", 1)
    return pagina.replace('<footer class="footer"', bloco + '<footer class="footer"', 1)
