"""AlphaFest HF65.22: uma fonte editorial para site e YouTube.

Nenhuma operacao publica, conecta contas ou aciona YouTube sem permissao.
A secao permanece desligada ate a aprovacao individual de cada guia.
"""
from __future__ import annotations

import html
import json
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

DOMINIO = "https://alphafest.com.br"
TITULO_SECAO = "Dicas & Inspirações AlphaFest"
CANAL_YOUTUBE_OFICIAL = "https://www.youtube.com/@AlphafestItatiba2026"


def _slug(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = texto.encode("ascii", "ignore").decode("ascii").lower()
    texto = re.sub(r"[^a-z0-9]+", "-", texto).strip("-")[:72]
    return texto or "dica"


def _article(title: str, summary: str, body: str, script: str) -> Dict[str, str]:
    return {
        "slug": _slug(title), "title": title, "summary": summary,
        "body": body.strip(), "script": script.strip(),
        "status": "rascunho", "video_id": "", "youtube_status": "nao_enviado",
    }


DEFAULT_DICAS = [
    _article(
        "Como planejar uma festa infantil sem estourar o orçamento",
        "Um passo a passo para organizar uma comemoração bonita, prática e com prioridades claras.",
        """## Comece pelo que realmente importa
Uma festa não precisa ter dezenas de itens para ser especial. Antes de escolher o tema, defina quantas pessoas serão convidadas, onde o evento acontecerá e quanto poderá investir. Reserve uma pequena margem para imprevistos: transporte, gelo, itens descartáveis e necessidades de última hora costumam passar despercebidos.

## Monte uma lista em três grupos
Divida as compras em essenciais, desejáveis e extras. Os essenciais incluem local, alimentação, bebidas, bolo e uma estrutura adequada para receber os convidados. Os desejáveis podem ser o painel, os balões e lembrancinhas. Os extras são elementos decorativos que só entram se ainda houver espaço no orçamento.

## Escolha um tema que funcione em diferentes materiais
Cores coordenadas ajudam a repetir a identidade da festa em convites, tags, decoração e topo de bolo. Não é necessário colocar o mesmo personagem em tudo. Uma combinação de duas ou três cores cria unidade visual e costuma facilitar as compras.

## Evite desperdícios nas lembrancinhas
Pense no número real de convidados e na idade das crianças. Uma lembrança útil ou uma embalagem personalizada simples pode ter mais valor do que vários objetos sem função. Se houver uma atividade na festa, a própria peça produzida pode ser a lembrança.

## Antecipe a produção dos personalizados
Convites, adesivos, painéis e displays precisam de tempo para arte, conferência e fabricação. Revisar nomes, idades e quantidades antes da impressão evita gastos com refações.

## Feche com um checklist
Uma semana antes, confirme local, fornecedores, horários e a lista de compras. Na véspera, organize a sequência de montagem, transporte e itens que precisam de refrigeração. No dia, deixe uma pessoa responsável por receber as entregas. Assim você aproveita a comemoração em vez de resolver detalhes o tempo todo.

A AlphaFest pode ajudar a montar uma identidade visual coordenada para a sua festa, com personalizados produzidos conforme o tema e a quantidade desejada.""",
        "Planejar uma festa infantil não precisa estourar o orçamento. Primeiro, defina convidados, local e valor máximo. Depois separe itens essenciais, desejáveis e extras. Escolha duas ou três cores para combinar convite, balões e lembrancinhas. Encomende personalizados com antecedência e revise os nomes antes da impressão. Quer ideias para sua festa? Acesse alphafest.com.br.",
    ),
    _article(
        "Arco de balões: tradicional ou desconstruído?",
        "Entenda as diferenças e descubra qual estilo combina melhor com o seu espaço e ocasião.",
        """## O efeito do arco tradicional
O arco tradicional tem uma distribuição mais regular dos balões. Sua aparência organizada funciona bem em entradas, painéis e eventos em que a decoração precisa acompanhar uma identidade visual precisa. É possível variar as cores para destacar a marca ou o tema.

## O que muda no desconstruído
No arco desconstruído, balões de tamanhos diferentes criam movimento e volume. O resultado é mais orgânico e pode funcionar como protagonista de um painel fotográfico. Esse estilo costuma pedir atenção especial ao equilíbrio de tamanhos e à distribuição de cores.

## Com ou sem estrutura?
O formato de instalação depende do lugar. Uma estrutura própria pode facilitar o posicionamento de um arco, enquanto instalações sem estrutura precisam ser avaliadas conforme superfície, vento e fixações disponíveis. Para eventos ao ar livre, a segurança da montagem é tão importante quanto a estética.

## Como escolher as cores
Para aniversários delicados, duas cores e um detalhe metalizado podem ser suficientes. Temas infantis mais vibrantes combinam bem com contrastes. Já em eventos corporativos, vale reproduzir as cores da marca de forma equilibrada.

## Planejamento e manutenção
Informe ao profissional onde o arco ficará, se haverá sol direto, vento ou circulação intensa. Temperatura e condições de exposição afetam a durabilidade dos balões. Evite deixá-los próximos a fontes de calor e objetos pontiagudos.

## Qual escolher?
Se a prioridade é regularidade e um visual clássico, considere o tradicional. Para um efeito cenográfico e volumoso, o desconstruído pode ser melhor. Uma foto do local e as medidas disponíveis ajudam a definir a solução correta.

Na AlphaFest, você pode consultar opções de arcos e decoração com balões de acordo com seu evento e espaço.""",
        "Você sabe a diferença entre arco de balões tradicional e desconstruído? O tradicional tem balões distribuídos de forma regular. O desconstruído mistura tamanhos para criar um visual mais orgânico. Para escolher, pense no tamanho do espaço, no local de instalação e nas cores do evento. Veja ideias no site alphafest.com.br.",
    ),
    _article(
        "Lembrancinhas personalizadas: ideias úteis para cada ocasião",
        "Como escolher lembranças que combinam com o evento e continuam úteis depois da festa.",
        """## A lembrança começa com o público
Antes de definir o produto, pense em quem vai receber. Em festas infantis, itens adequados à faixa etária e embalagens seguras são prioridade. Para professores ou equipes de trabalho, o uso cotidiano pode ser o principal critério.

## Papelaria personalizada
Tags, adesivos, cartões e caixas ajudam a transformar produtos simples em lembranças com identidade própria. A vantagem está na possibilidade de adaptar cores, mensagens e quantidades sem perder a unidade visual do evento.

## Canecas, copos e ecobags
Produtos reutilizáveis podem acompanhar a rotina de quem recebe. Vale priorizar uma arte legível, que combine com o estilo da pessoa e não apenas com o tema da festa.

## Peças 3D e projetos especiais
Chaveiros, suportes e pequenos objetos produzidos em impressão 3D permitem formas diferentes. Sempre avalie tamanho, resistência e adequação ao uso pretendido.

## Personalização ao vivo
Em uma oficina durante a festa, os convidados podem escolher entre estampas previamente aprovadas e acompanhar a personalização de uma camiseta, boné ou ecobag. É uma experiência que une entretenimento e lembrança, mas exige planejamento de equipamento, tempo e segurança.

## Quantidade e apresentação
Faça a conta considerando o número real de convidados e algumas peças de reserva. Combine a embalagem com as cores do evento e revise nomes e datas antes de autorizar a produção.

A AlphaFest oferece papelaria, produtos personalizados e opções de lembranças para aniversários, escolas, empresas e ocasiões especiais.""",
        "Quer escolher uma lembrancinha que as pessoas realmente usem? Pense em quem vai receber. Tags e caixas dão identidade à festa. Canecas, copos e ecobags funcionam no dia a dia. Peças 3D podem criar algo diferente. E oficinas de personalização transformam a lembrança em atração! Confira ideias em alphafest.com.br.",
    ),
    _article(
        "Brindes personalizados para empresas: como escolher sem desperdiçar",
        "Um guia para conectar orçamento, finalidade e identidade da marca na escolha de brindes.",
        """## Defina o objetivo do brinde
Um presente para uma equipe interna pode ter características diferentes de um item distribuído em uma feira. Pergunte o que você quer que as pessoas lembrem: a marca, uma campanha, uma data ou um agradecimento.

## Conheça o público
Um brinde útil faz mais sentido quando acompanha a rotina de quem o recebe. Ecobags podem ser práticas em eventos, canecas podem funcionar como presente de reconhecimento e itens de papelaria podem complementar um kit de boas-vindas.

## Pense no uso antes de escolher a técnica
Materiais diferentes pedem acabamentos diferentes. Avalie área de impressão, cores do logotipo, resistência e cuidados de limpeza. Nem toda arte fica legível quando reduzida; antes da produção, peça uma visualização na medida real.

## Planeje a quantidade com cuidado
A tiragem influencia organização e custo unitário. Faça a previsão com base em participantes confirmados e uma margem sensata para reposição. Evite encomendar itens apenas porque a quantidade maior parece mais barata.

## Prepare o arquivo da marca
Use uma versão de boa resolução do logotipo, respeite as cores oficiais e confira textos e contatos. Quando houver versões horizontal e vertical, escolha a que combina com o produto em vez de comprimir a arte.

## Antecedência evita urgências
Defina prazo interno para aprovação da arte e reserve tempo para eventuais ajustes. Em kits com vários produtos, confira se os itens poderão ser entregues e embalados juntos.

A AlphaFest pode ajudar na escolha de brindes e materiais gráficos personalizados para equipes, eventos e campanhas empresariais.""",
        "Brinde de empresa não é só colocar um logo em qualquer produto. Primeiro defina o objetivo e quem vai receber. Depois escolha algo útil, como caneca, ecobag ou papelaria. Confira se o logotipo continua legível no tamanho real e planeje a quantidade com antecedência. Conheça as opções da AlphaFest em alphafest.com.br.",
    ),
]


def normalize_dicas(data: Any) -> List[Dict[str, str]]:
    """Retorna dados simples, sem aceitar HTML ou scripts do editor."""
    if not isinstance(data, list):
        return [dict(x) for x in DEFAULT_DICAS]
    output = []
    usados = set()
    for item in data[:80]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()[:130]
        if not title:
            continue
        slug = _slug(item.get("slug") or title)
        if slug in usados:
            continue
        usados.add(slug)
        vid = str(item.get("video_id") or "").strip()
        m = re.fullmatch(r"[A-Za-z0-9_-]{11}", vid)
        output.append({
            "slug": slug,
            "title": title,
            "summary": str(item.get("summary") or "").strip()[:300],
            "body": str(item.get("body") or "").strip()[:16000],
            "script": str(item.get("script") or "").strip()[:3000],
            "status": "publicado" if item.get("status") == "publicado" else "rascunho",
            "video_id": vid if m else "",
            "youtube_status": (str(item.get("youtube_status")) if str(item.get("youtube_status")) in ("publicado", "privado") else "nao_enviado") if m else "nao_enviado",
        })
    return output


def dicas_publicadas(data: Any) -> List[Dict[str, str]]:
    return [x for x in normalize_dicas(data) if x["status"] == "publicado" and x["body"]]


def _safe(v: Any) -> str:
    return html.escape(str(v or ""), quote=True)


def _body_to_html(body: str) -> str:
    nodes = []
    for block in re.split(r"\n\s*\n", str(body or "").strip()):
        b = block.strip()
        if not b:
            continue
        if b.startswith("## "):
            nodes.append(f"<h2>{_safe(b[3:])}</h2>")
        else:
            nodes.append("<p>" + _safe(b).replace("\n", "<br>") + "</p>")
    return "".join(nodes)


CSS = """
:root{color-scheme:light;--azul:#065ea9;--bg:#f5fbff;--texto:#19354b}
*{box-sizing:border-box}body{margin:0;font-family:Arial,Helvetica,sans-serif;color:var(--texto);background:white;line-height:1.68}
header{background:linear-gradient(120deg,#0056a7,#189bdb);color:white;padding:23px max(24px,calc((100vw - 1050px)/2));}
header a{color:white;text-decoration:none;font-weight:700}main{max-width:1050px;margin:0 auto;padding:36px 24px 70px}
h1{font-size:clamp(2rem,4vw,2.8rem);line-height:1.2;color:#053f7a}h2{margin-top:34px;color:#065ea9}
.lead{font-size:1.15rem;color:#41657c}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:20px;margin-top:30px}
.card{border:1px solid #d7e9f6;background:#f8fcff;border-radius:18px;padding:24px;box-shadow:0 4px 14px #0a589214}
.card h2{font-size:1.23rem;margin:0 0 10px}.card p{margin-top:0}.card a,.cta{display:inline-block;color:#005cae;font-weight:bold}
article{max-width:800px}article p{margin:15px 0}aside{padding:22px;background:#f0faff;border-left:4px solid #0d87cc;margin:30px 0}
.video{position:relative;padding-top:56.25%;background:#041f33;border-radius:16px;overflow:hidden;margin:25px 0}
.video iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
.whatsapp{background:#0a6cb4;color:white!important;padding:12px 18px;border-radius:12px;text-decoration:none}
footer{border-top:1px solid #dfebf2;padding:25px;text-align:center;color:#587187;font-size:.94rem}
"""


def _page(title: str, description: str, url: str, content: str, schema: Dict[str, Any] | None = None) -> str:
    structured = (f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False).replace("<", "\\u003c")}</script>' if schema else "")
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{_safe(title)} | AlphaFest</title><meta name="description" content="{_safe(description)}">'
            f'<link rel="canonical" href="{_safe(url)}"><meta name="robots" content="index,follow">'
            f'<style>{CSS}</style>{structured}</head><body><header><a href="/">AlphaFest</a>　/　'
            f'<a href="/dicas/">Dicas & Inspirações</a></header><main>{content}</main>'
            f'<footer>AlphaFest · Itatiba, SP · <a href="/">Voltar à loja</a> · '
            f'<a href="{CANAL_YOUTUBE_OFICIAL}" rel="noopener noreferrer" target="_blank">Canal oficial no YouTube</a>'
            f'</footer></body></html>')


def paginas_dicas(data: Any, whatsapp: str = "") -> Dict[str, str]:
    posts = dicas_publicadas(data)
    if not posts:
        return {}
    output = {}
    cards = ''.join(f'<div class="card"><h2>{_safe(p["title"])}</h2><p>{_safe(p["summary"])}</p>'
                    f'<a href="/dicas/{p["slug"]}/">Ler guia completo</a></div>' for p in posts)
    output["dicas/index.html"] = _page(TITULO_SECAO, "Guias práticos sobre festas, balões e personalizados.", DOMINIO+"/dicas/",
        f'<h1>{TITULO_SECAO}</h1><p class="lead">Ideias práticas para celebrar, presentear e personalizar.</p><div class="grid">{cards}</div>')
    numero = re.sub(r"\D", "", str(whatsapp or ""))
    if numero and not numero.startswith("55"):
        numero = "55" + numero
    wa_link = "https://wa.me/" + numero if numero else "https://alphafest.com.br/"
    for p in posts:
        url = f'{DOMINIO}/dicas/{p["slug"]}/'
        vid = p["video_id"] if p["youtube_status"] == "publicado" else ""
        video_html = (f'<h2>Assista também no YouTube</h2><div class="video"><iframe loading="lazy" allowfullscreen '
                      f'referrerpolicy="strict-origin-when-cross-origin" title="Vídeo AlphaFest" '
                      f'src="https://www.youtube-nocookie.com/embed/{vid}"></iframe></div>') if vid else ""
        schema = {"@context":"https://schema.org","@type":"BlogPosting","headline":p["title"],
                  "description":p["summary"],"inLanguage":"pt-BR","mainEntityOfPage":url,
                  "author":{"@type":"Organization","name":"AlphaFest"},
                  "publisher":{"@type":"Organization","name":"AlphaFest","url":DOMINIO}}
        content = (f'<article><p><a href="/dicas/">← Todos os guias</a></p><h1>{_safe(p["title"])}</h1>'
                   f'<p class="lead">{_safe(p["summary"])}</p>{_body_to_html(p["body"])}{video_html}'
                   f'<aside><strong>Personalize com a AlphaFest</strong><p>Confira nossos produtos ou peça uma ideia para o seu evento.</p>'
                   f'<a class="whatsapp" href="{_safe(wa_link)}" rel="noopener">Falar com a AlphaFest</a></aside></article>')
        output[f'dicas/{p["slug"]}/index.html'] = _page(p["title"],p["summary"],url,content,schema)
    return output


def inserir_chamada_dicas(html_site: str, data: Any) -> str:
    posts = dicas_publicadas(data)
    pagina = str(html_site or "")
    if not posts:
        return pagina
    cards = "".join(f'<a href="/dicas/{x["slug"]}/" class="alpha-dicas-card"><strong>{_safe(x["title"])}</strong>'
                    f'<span>{_safe(x["summary"])}</span><b>Ler dica →</b></a>' for x in posts[:4])
    bloco = ('<section id="dicas-alphafest" class="alpha-dicas-wrap" aria-label="Dicas e Inspirações">'
             f'<div class="alpha-dicas-inner"><h2>{TITULO_SECAO}</h2><p>Ideias para festas, lembranças e presentes.</p>'
             f'<div class="alpha-dicas-grid">{cards}</div><a class="alpha-dicas-all" href="/dicas/">Ver todas as dicas</a></div></section>')
    style = '''<style id="alphafest-dicas-style">.alpha-dicas-wrap{padding:48px 20px;background:#f4fbff;color:#154267}.alpha-dicas-inner{max-width:1140px;margin:auto}.alpha-dicas-wrap h2{font-size:clamp(1.6rem,2vw,2.2rem);color:#0763a9}.alpha-dicas-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:17px;margin:22px 0}.alpha-dicas-card{border:1px solid #d6e9f5;border-radius:14px;padding:19px;background:white;display:flex;flex-direction:column;gap:10px;text-decoration:none;color:#184462}.alpha-dicas-card span{font-size:.92rem}.alpha-dicas-card b,.alpha-dicas-all{color:#0067ae}</style>'''
    if "</head>" in pagina:
        pagina=pagina.replace("</head>",style+"</head>",1)
    pos=pagina.find('<footer class="footer"')
    if pos < 0: pos=pagina.find("</body>")
    return pagina[:pos]+bloco+pagina[pos:] if pos>=0 else pagina


def youtube_export_text(data: Dict[str, str]) -> Dict[str, str]:
    url = f'{DOMINIO}/dicas/{data["slug"]}/'
    title = data["title"][:100]
    description = (f'{data["summary"]}\n\nLeia o guia completo: {url}\n'
                   f'Conheça a AlphaFest: {DOMINIO}/\n'
                   f'Canal oficial: {CANAL_YOUTUBE_OFICIAL}\n\n#AlphaFest #FestasPersonalizadas #DicasDeFesta #Shorts')
    return {"title":title,"description":description,"script":data["script"],"source_url":url}
