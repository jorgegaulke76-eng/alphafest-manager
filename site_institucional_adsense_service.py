"""Páginas institucionais públicas da AlphaFest para orientação e transparência.

Conteúdo estático, sem dependências externas, não ativa anúncios nem altera pedidos.
"""
from __future__ import annotations

from html import escape

DOMINIO = "https://alphafest.com.br"


def _pagina(titulo: str, descricao: str, slug: str, corpo: str) -> str:
    """Página leve, responsiva e indexável, sem scripts ou anúncios."""
    url = f"{DOMINIO}/{slug}/"
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{url}">
<meta name="description" content="{escape(descricao, quote=True)}">
<title>{escape(titulo)} | AlphaFest</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;font:16px/1.7 system-ui,Arial,sans-serif;background:#f5faff;color:#17344e}}
header{{background:#086caf;color:white;padding:24px max(18px,calc((100% - 960px)/2))}}
header a{{color:white;text-decoration:underline}}main{{max-width:960px;margin:0 auto;padding:24px 18px 52px}}
article{{background:white;border:1px solid #dbe8f3;border-radius:16px;padding:clamp(20px,4vw,45px)}}
h1{{font-size:clamp(1.6rem,4vw,2.5rem);line-height:1.2;margin:0 0 10px}}h2{{font-size:1.35rem;line-height:1.35;margin:28px 0 8px}}
p,li{{max-width:78ch}}a{{color:#075d9b}}a:focus-visible{{outline:3px solid #f2a900;outline-offset:3px}}
footer{{text-align:center;padding:20px;color:#456078}}footer a{{margin:0 8px}}
@media(max-width:500px){{article{{padding:18px}}}}
</style>
</head>
<body><header><a href="/">← Voltar ao site AlphaFest</a></header>
<main><article><h1>{escape(titulo)}</h1>{corpo}</article></main>
<footer>AlphaFest · Itatiba, SP · <a href="/">Página inicial</a>
<a href="/privacidade/">Privacidade</a> <a href="/como-encomendar/">Como encomendar</a></footer>
</body></html>"""


PRIVACIDADE = """
<p>Esta política explica como informações podem ser tratadas quando você visita o site AlphaFest,
consulta produtos ou entra em contato para encomendar personalizados. Última atualização: 26/11/2026.</p>
<h2>Quem é responsável pelo site?</h2>
<p>AlphaFest — Personalizados &amp; Balões, em Itatiba, São Paulo. Para dúvidas sobre privacidade,
escreva para <a href="mailto:alphafesti@gmail.com">alphafesti@gmail.com</a>.</p>
<h2>Dados de navegação e métricas</h2>
<p>O site utiliza infraestrutura de hospedagem e serviços técnicos para carregar páginas,
imagens e acompanhar o funcionamento da vitrine. Dados técnicos como endereço IP, tipo de
navegador, dispositivo, páginas visitadas e horários podem ser tratados pelos provedores
de infraestrutura para operação, segurança e diagnóstico.</p>
<p>Para entender quais áreas do site são mais úteis, também podem ser registrados eventos
como abertura de produtos, pesquisas e cliques em botões, a origem aproximada do acesso,
parâmetros de campanha e localização aproximada (cidade, região ou país).
Identificadores de visita e sessão podem ser armazenados no próprio navegador
por mecanismos como armazenamento local e de sessão (localStorage e sessionStorage).</p>
<h2>Pedidos, mensagens e contato</h2>
<p>Quando você clica para conversar pelo WhatsApp ou nos procura por e-mail,
as informações que decidir enviar — por exemplo nome, telefone, referências, imagens
e detalhes da encomenda — são usadas para responder, preparar orçamentos e acompanhar
a solicitação. O envio e a utilização de dados nessas plataformas também seguem as
políticas dos respectivos serviços.</p>
<h2>Serviços de terceiros</h2>
<p>O site pode utilizar Cloudflare para disponibilização das páginas, Supabase para
conteúdo e métricas, e links para WhatsApp e outros serviços externos.
Esses fornecedores podem processar dados técnicos necessários às funcionalidades.</p>
<h2>Publicidade do Google e cookies</h2>
<p>O site está em processo de integração com o Google AdSense. Se a exibição de
anúncios for ativada, fornecedores terceiros, incluindo o Google, poderão colocar
e ler cookies no navegador ou utilizar identificadores, endereços IP e tecnologias
como web beacons para fornecer e medir anúncios. Cookies de publicidade podem ser
utilizados para apresentar anúncios com base em visitas a este e a outros sites.
Você pode consultar e ajustar preferências de anúncios em
<a href="https://adssettings.google.com/" rel="noopener noreferrer">Configurações de Anúncios do Google</a>.
Veja também <a href="https://policies.google.com/technologies/partner-sites?hl=pt-BR"
rel="noopener noreferrer">como o Google utiliza informações de sites e aplicativos parceiros</a>.</p>
<h2>Uso, retenção e direitos</h2>
<p>Os dados são utilizados para funcionamento do site, atendimento, segurança,
medição de uso e cumprimento de obrigações aplicáveis. O período de retenção pode
variar conforme a finalidade e exigências legais. Você pode solicitar informações,
acesso, correção ou exclusão de dados pessoais, conforme a legislação aplicável,
pelo e-mail informado acima.</p>
<p>Esta política poderá ser atualizada quando houver mudanças nas ferramentas
ou na forma de atendimento.</p>
"""

COMO_ENCOMENDAR = """
<p>Um pedido personalizado começa por informações simples: o que será produzido,
para quando será usado e o resultado que você deseja. Este guia ajuda a preparar
seu orçamento sem esquecer detalhes importantes.</p>
<h2>1. Defina a ocasião e a finalidade</h2>
<p>Explique se o produto será usado em aniversário, casamento, escola, evento empresarial
ou presente. Para uma lembrancinha, pense na faixa etária e na quantidade de convidados;
para um brinde corporativo, considere o público e o uso esperado após o evento.</p>
<h2>2. Organize as medidas e quantidades</h2>
<p>Inclua quantidade, tamanho aproximado e formato. Um adesivo redondo de 4 cm,
por exemplo, tem uma área útil bem diferente de uma arte impressa em folha A4.
Para papelaria, informe a superfície em que a peça será aplicada. Para canecas,
ecobags e camisetas, a dimensão da estampa influencia a leitura do desenho.</p>
<h2>3. Reúna as referências visuais</h2>
<p>Envie cores, nomes, frases e imagens de referência que ajudem a descrever o estilo.
Se o projeto usar logotipo, prefira um arquivo com boa definição. Esclareça se deseja
uma arte digital ou um item já produzido. Antes da impressão, confira atentamente
grafia, datas, idade e contatos.</p>
<h2>4. Planeje o prazo com antecedência</h2>
<p>O tempo de confecção depende do material, da quantidade, da etapa de criação e
da agenda de produção. Informe a data do evento já no primeiro contato e inclua
a necessidade de montagem, retirada ou entrega na conversa. Disponibilidade e
prazo devem ser confirmados no orçamento.</p>
<h2>5. Cuidados conforme o tipo de produto</h2>
<p><strong>Balões:</strong> informe se a montagem será interna ou externa, as medidas
do espaço e a exposição ao sol e vento. <strong>Impressão 3D:</strong> indique
a função da peça, medidas e possíveis encaixes. <strong>Gravação a laser:</strong>
informe o material e a área de gravação. <strong>Brindes:</strong> pense na
legibilidade da marca e no uso real do objeto.</p>
<h2>6. Solicite a avaliação da AlphaFest</h2>
<p>O catálogo apresenta exemplos de produtos e trabalhos. Como cada projeto pode
variar em tamanho, material, arte e quantidade, os valores e prazos são confirmados
pela equipe conforme os detalhes solicitados. A consulta não constitui compra automática.</p>
<p><a href="/">Conheça a vitrine de produtos</a> ou
<a href="https://wa.me/5511972949533" rel="noopener noreferrer">converse com a AlphaFest no WhatsApp</a>.</p>
"""


def paginas_institucionais() -> dict[str, str]:
    return {
        "privacidade/index.html": _pagina(
            "Política de Privacidade",
            "Como o site AlphaFest trata dados de navegação, contato, métricas e publicidade.",
            "privacidade",
            PRIVACIDADE,
        ),
        "como-encomendar/index.html": _pagina(
            "Como encomendar personalizados",
            "Guia prático para pedir personalizados, balões, brindes e peças em impressão 3D.",
            "como-encomendar",
            COMO_ENCOMENDAR,
        ),
    }


def inserir_links_institucionais(pagina: str) -> str:
    """Inclui links permanentes no rodapé sem duplicar na republicação."""
    pagina = str(pagina or "")
    if 'id="af-links-institucionais"' in pagina or "</footer>" not in pagina:
        return pagina
    links = (
        '<nav id="af-links-institucionais" aria-label="Informações do site" '
        'style="display:flex;justify-content:center;flex-wrap:wrap;gap:14px;'
        'padding:16px 12px;font-size:14px">'
        '<a href="/privacidade/">Política de Privacidade</a>'
        '<a href="/como-encomendar/">Como encomendar</a>'
        '</nav>'
    )
    return pagina.replace("</footer>", links + "</footer>", 1)
