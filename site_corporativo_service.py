"""HF65.24.26 — página de orçamento corporativo sem cadastro ou armazenamento de dados pessoais."""
from __future__ import annotations
import html
import re
import base64
import io
from pathlib import Path
from urllib.parse import quote


def _numero(empresa):
    n = re.sub(r'\D', '', str((empresa or {}).get('whatsapp_catalogo') or (empresa or {}).get('celular') or ''))
    return ('55' + n if n and not n.startswith('55') else n)


def inject_corporate_home(pagina: str) -> str:
    if 'id="corporativo-alphafest"' in pagina:
        return pagina
    bloco = '''<style id="hf652426-corp-style">
    #corporativo-alphafest{background:linear-gradient(120deg,#eef8ff,#fff);padding:36px 20px;color:#163759}
    #corporativo-alphafest .corp-in{max-width:1120px;margin:auto;display:flex;align-items:center;justify-content:space-between;gap:24px;flex-wrap:wrap}
    #corporativo-alphafest h2{font-size:clamp(23px,3vw,32px);margin:6px 0 10px}
    #corporativo-alphafest p{max-width:650px;margin:0;color:#42617a;line-height:1.55}
    #corporativo-alphafest a{background:#0b79cf;color:white;text-decoration:none;font-weight:700;padding:13px 21px;border-radius:12px;white-space:nowrap}
    </style><section id="corporativo-alphafest" aria-label="Brindes personalizados para empresas"><div class="corp-in"><div><span style="color:#1166a8;font-weight:800">ALPHAFEST PARA EMPRESAS</span><h2>Brindes corporativos com a sua marca</h2><p>Presentes para colaboradores, clientes, eventos e confraternizações. Conte sua ideia, quantidade e prazo para receber um orçamento personalizado.</p></div><a href="/empresas/">Solicitar orçamento empresarial</a></div></section>'''
    pos=pagina.find('<main class="main" id="produtos">')
    if pos < 0:
        pos=pagina.find('</main>')
    if pos < 0:
        pos=pagina.find('</body>')
    if pos >= 0:
        pagina=pagina[:pos]+bloco+pagina[pos:]
    nav_match=re.search(r'(<nav class="site-nav"[^>]*>\s*<div class="site-nav-in"[^>]*>)(.*?)(</div>\s*</nav>)', pagina, flags=re.S)
    if nav_match and 'href="/empresas/"' not in nav_match.group(2):
        pagina=pagina[:nav_match.start(3)]+'<a href="/empresas/">Para Empresas</a>'+pagina[nav_match.start(3):]
    return pagina


def _foto_leve(src: str) -> str:
    """Miniatura derivada para a vitrine, nunca modifica a imagem original."""
    if not src.startswith('data:image/'):
        return src if src.startswith(('https://', 'http://')) else ''
    try:
        from PIL import Image
        cabecalho, dados = src.split(',', 1)
        if 'base64' not in cabecalho:
            return ''
        foto = Image.open(io.BytesIO(base64.b64decode(dados)))
        foto.thumbnail((480, 420))
        if foto.mode not in ('RGB', 'RGBA'):
            foto = foto.convert('RGB')
        arquivo = io.BytesIO()
        foto.save(arquivo, format='WEBP', quality=76, method=3)
        return 'data:image/webp;base64,' + base64.b64encode(arquivo.getvalue()).decode('ascii')
    except Exception:
        return ''


def _galeria_produtos_corporativos(produtos, imagem_resolver=None):
    """Somente itens publicados no Catálogo oficial; nenhuma imagem de banco paralela."""
    try:
        from site_vitrine_service import selecionar_produtos_vitrine
        selecionados = selecionar_produtos_vitrine(produtos or [], usar_taxonomia_catalogo=False)
    except Exception:
        return ''
    grupos = (
        ('Canecas e copos', ('caneca', 'copo', 'taça', 'squeeze', 'garrafa')),
        ('Brindes e chaveiros', ('chaveiro', 'brinde', '3d', 'troféu')),
        ('Papelaria e etiquetas', ('etiqueta', 'adesivo', 'papelaria', 'tag', 'cartão')),
        ('Eventos e equipes', ('crachá', 'cordão', 'ecobag', 'camiseta', 'sacola')),
    )
    cards = []
    usados = set()
    for rotulo, termos in grupos:
        for item in selecionados:
            nome = str(item.get('nome') or '').strip()
            src = str(item.get('imagem_principal') or '').strip()
            chave = (nome.casefold(), src)
            if not nome or not src or chave in usados:
                continue
            corpus = ' '.join([nome, str(item.get('categoria') or ''), str(item.get('subcategoria') or '')]).casefold()
            if not any(t in corpus for t in termos):
                continue
            if imagem_resolver:
                try:
                    src = str(imagem_resolver(src) or '')
                except Exception:
                    continue
            thumb = _foto_leve(src)
            if not thumb:
                continue
            usados.add(chave)
            cards.append('<figure class="corp-prod"><img src="'+html.escape(thumb,quote=True)+'" loading="lazy" decoding="async" alt="'+html.escape(nome,quote=True)+'"><figcaption>'+html.escape(nome)+'</figcaption></figure>')
            break
    if not cards:
        return ''
    return ('<div class="corp-real-gallery"><h3>Alguns dos nossos produtos</h3>'
            '<p class="note">Fotos de produtos do Catálogo AlphaFest. Modelos e personalizações sob consulta.</p>'
            '<div class="corp-photo-grid">'+''.join(cards)+'</div></div>')


def corporate_page(empresa: dict, *, produtos=None, imagem_resolver=None, logo_src: str = '', site_shell_html: str = '') -> str:
    telefone=_numero(empresa)
    safe_phone=html.escape(telefone,quote=True)
    # Form only builds a wa.me link on user click. No site-side storage or network submission.
    pagina = '''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Brindes corporativos em Itatiba | AlphaFest</title><meta name="description" content="Solicite orçamento de brindes e presentes personalizados para empresas em Itatiba. Canecas, kits, chaveiros, impressão 3D e papelaria."><link rel="canonical" href="https://alphafest.com.br/empresas/"><meta name="theme-color" content="#0796e8"><style>
    *{box-sizing:border-box}body{margin:0;font-family:system-ui,Arial,sans-serif;color:#143455;background:#f3f9ff;line-height:1.5}header.corp-hero{background:linear-gradient(110deg,#0877cc,#08b1e4);color:#fff;padding:24px max(20px,calc((100% - 1120px)/2))}header.corp-hero a{color:#fff}header.corp-hero h1{font-size:clamp(25px,4vw,42px);margin:13px 0 4px}header.corp-hero p{max-width:700px;margin:0}main{max-width:1120px;margin:28px auto;padding:0 18px}.layout{display:grid;grid-template-columns:1fr 1.1fr;gap:24px;align-items:start}section,.panel{background:#fff;border:1px solid #dceafb;border-radius:18px;padding:24px;box-shadow:0 5px 22px #17466f0b}h2{margin:0 0 15px;color:#0863a7}ul{padding-left:22px}li{margin-bottom:12px}.note{color:#53718a;font-size:14px}#corp-form label{display:block;font-weight:700;margin:14px 0 5px}#corp-form input,#corp-form select,#corp-form textarea{width:100%;padding:12px;border:1px solid #b8d3ea;border-radius:9px;font:inherit;background:#fff;color:#183c5e}#corp-form textarea{resize:vertical}#corp-form button{width:100%;background:#16bd60;color:#fff;padding:15px;border:0;border-radius:11px;font-weight:800;font-size:16px;cursor:pointer;margin-top:20px}#corp-form button:hover{background:#099e4b}.tiny{font-size:12px;color:#5b7188}footer.corp-simple-footer{text-align:center;padding:22px;color:#426482}@media(max-width:760px){.layout{grid-template-columns:1fr}section,.panel{padding:18px}}
    </style></head><body><header class="corp-hero"><a href="/">← Voltar ao site AlphaFest</a><h1>Brindes corporativos AlphaFest</h1><p>Personalizados para equipes, clientes, fornecedores, eventos e confraternizações. Orçamento feito sob medida para a sua empresa.</p></header><main><div class="layout"><section><h2>Ideias para sua empresa</h2><ul><li><strong>Canecas e copos:</strong> lembranças para equipes e clientes</li><li><strong>Chaveiros e brindes em 3D:</strong> formatos personalizados</li><li><strong>Etiquetas, adesivos e papelaria:</strong> identidade visual da sua marca</li><li><strong>Kits de fim de ano:</strong> combinações conforme quantidade e orçamento</li><li><strong>Itens para eventos:</strong> crachás, cordões e presentes promocionais</li></ul><p class="note">Valores e prazos dependem da arte, técnica, quantidade, materiais e agenda de produção. O orçamento não representa uma compra.</p><a href="/#produtos">Conhecer os produtos do catálogo</a></section><div class="panel"><h2>Solicitar orçamento</h2><p class="note">Preencha os detalhes e revise a mensagem no WhatsApp antes de enviar.</p><form id="corp-form"><label for="corp-item">O que deseja personalizar?</label><select id="corp-item" required><option value="">Selecione uma opção</option><option>Canecas e copos</option><option>Kits corporativos</option><option>Chaveiros e impressão 3D</option><option>Crachás e cordões</option><option>Adesivos, etiquetas e papelaria</option><option>Outros personalizados</option></select><label for="corp-qtd">Quantidade aproximada</label><input id="corp-qtd" type="number" min="1" max="100000" step="1" placeholder="Ex.: 30" required><label for="corp-faixa">Faixa de orçamento (opcional)</label><select id="corp-faixa"><option value="">Prefiro conversar</option><option>Até R$ 500</option><option>R$ 500 a R$ 1.000</option><option>R$ 1.000 a R$ 2.500</option><option>Acima de R$ 2.500</option></select><label for="corp-data">Data desejada (opcional)</label><input id="corp-data" type="date"><label for="corp-detalhes">Cores, personalização e detalhes</label><textarea id="corp-detalhes" rows="4" maxlength="1500" placeholder="Ex.: aplicar nossa logo nas canecas..."></textarea><button type="submit">Solicitar pelo WhatsApp</button><p class="tiny">Você será direcionado ao WhatsApp e poderá revisar a mensagem. Nenhum dado é armazenado neste formulário.</p></form></div></div></main><footer class="corp-simple-footer">AlphaFest · Estamos presentes em cada presente!</footer><script>
    (function(){const form=document.getElementById('corp-form');form.addEventListener('submit',function(e){e.preventDefault();if(!form.reportValidity())return;const v=id=>document.getElementById(id).value.trim();const linhas=['Olá, AlphaFest! Gostaria de um orçamento empresarial.','Produto: '+v('corp-item'),'Quantidade aproximada: '+v('corp-qtd')];if(v('corp-faixa'))linhas.push('Orçamento pretendido: '+v('corp-faixa'));if(v('corp-data')){let d=v('corp-data').split('-');linhas.push('Data desejada: '+d.reverse().join('/'));}if(v('corp-detalhes'))linhas.push('Detalhes: '+v('corp-detalhes'));linhas.push('Podem confirmar as opções, valores e prazos?');const tel='''+repr(telefone)+''';if(!tel){alert('WhatsApp indisponível. Entre em contato pelo site.');return;}window.open('https://wa.me/'+tel+'?text='+encodeURIComponent(linhas.join('\\n')),'_blank','noopener,noreferrer');});})();
    </script></body></html>'''

    # HF65.24.27 — identidade visual oficial e referências reais do catálogo.
    if not logo_src:
        try:
            arquivo = Path(__file__).resolve().parent / 'assets' / 'mascotes' / 'logo_wordmark.webp'
            logo_src = 'data:image/webp;base64,' + base64.b64encode(arquivo.read_bytes()).decode('ascii')
        except Exception:
            logo_src = ''
    logo_html = ('<a class="corp-logo-link" href="/" aria-label="Voltar à página inicial AlphaFest">'
                 '<img class="corp-logo" src="'+html.escape(logo_src,quote=True)+'" alt="AlphaFest Personalizados e Balões"></a>') if logo_src.startswith(('data:image/', 'https://')) else ''
    pagina = pagina.replace('<header class="corp-hero"><a href="/">← Voltar ao site AlphaFest</a>',
                            '<header class="corp-hero"><div class="corp-head">'+logo_html+'<a class="corp-back" href="/">← Voltar ao site AlphaFest</a></div>', 1)
    galeria = _galeria_produtos_corporativos(produtos, imagem_resolver=imagem_resolver)
    kits = ('''<div class="corp-kits" aria-label="Sugestões de kits corporativos"><h3>Sugestões de kits</h3>
    <p class="note">Composições ilustrativas, montadas conforme necessidade, quantidade e disponibilidade. Não são pacotes fechados.</p>
    <div class="corp-kit"><strong>Essencial</strong><span>Cartão ou tag personalizada + lembrança simples</span></div>
    <div class="corp-kit"><strong>Intermediário</strong><span>Caneca ou copo personalizado + embalagem e mensagem</span></div>
    <div class="corp-kit"><strong>Especial</strong><span>Combinação de brindes personalizados com apresentação para a equipe</span></div>
    <a class="corp-kit-cta" href="#corp-form">Solicitar composição personalizada</a></div>''')
    pagina = pagina.replace('<p class="note">Valores e prazos dependem', galeria+kits+'<p class="note">Valores e prazos dependem', 1)
    extra = '''
    .corp-head{display:flex;justify-content:space-between;align-items:center;gap:20px;flex-wrap:wrap}
    .corp-logo{width:min(300px,75vw);max-height:94px;object-fit:contain;object-position:left center}
    .corp-head .corp-back{font-size:14px;font-weight:600;color:#fff}
    .corp-real-gallery{margin:24px 0 18px}
    .corp-real-gallery h3,.corp-kits h3{margin:0 0 8px;color:#0863a7;font-size:19px}
    .corp-photo-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:12px}
    .corp-prod{margin:0;border:1px solid #dceafb;border-radius:13px;overflow:hidden;background:#f6fbff}
    .corp-prod img{display:block;width:100%;height:145px;object-fit:contain;background:#fff}
    .corp-prod figcaption{font-size:12px;font-weight:700;padding:9px;color:#143455;line-height:1.4}
    .corp-kits{margin:22px 0 16px}.corp-kit{border:1px solid #dceafb;border-radius:12px;padding:12px;margin:9px 0;display:flex;flex-direction:column;gap:3px;background:#f8fcff}
    .corp-kit strong{color:#075f9f}.corp-kit span{font-size:13px;color:#405e79}
    .corp-kit-cta{display:inline-block;margin:10px 0;color:#006cb8;font-weight:700}
    @media(max-width:380px){.corp-photo-grid{grid-template-columns:1fr}}
    '''
    pagina = pagina.replace('</style>',extra+'</style>',1)
    if site_shell_html:
        pagina = _usar_cabecalho_rodape_da_home(pagina, site_shell_html)
    # Identificação de serviço local para resultados de busca; não inventar endereço nem avaliações.
    import json as _seo_json
    seo_meta = (
        '<meta property="og:type" content="website">'
        '<meta property="og:locale" content="pt_BR">'
        '<meta property="og:url" content="https://alphafest.com.br/empresas/">'
        '<meta property="og:title" content="Brindes corporativos em Itatiba | AlphaFest">'
        '<meta property="og:description" content="Brindes e kits personalizados para empresas. Solicite orçamento de canecas, chaveiros, papelaria e impressão 3D em Itatiba.">'
        '<meta name="twitter:card" content="summary">'
    )
    dados = {'@context':'https://schema.org','@graph':[
        {'@type':'Service','name':'Brindes corporativos personalizados','serviceType':'Personalização de brindes para empresas',
         'provider':{'@type':'Organization','name':'AlphaFest','url':'https://alphafest.com.br/'},
         'areaServed':{'@type':'City','name':'Itatiba'},'url':'https://alphafest.com.br/empresas/'},
        {'@type':'BreadcrumbList','itemListElement':[
            {'@type':'ListItem','position':1,'name':'AlphaFest','item':'https://alphafest.com.br/'},
            {'@type':'ListItem','position':2,'name':'Para Empresas','item':'https://alphafest.com.br/empresas/'}]}
    ]}
    seo_meta += '<script id="af-corporate-seo" type="application/ld+json">'+_seo_json.dumps(dados,ensure_ascii=False,separators=(',',':'))+'</script>'
    pagina = pagina.replace('</head>',seo_meta+'</head>',1)
    return pagina


def _usar_cabecalho_rodape_da_home(pagina: str, home: str) -> str:
    """Reaproveita elementos reais da Home, sem criar uma identidade paralela.

    Opera só na cópia HTML publicada: não altera dados, catálogo ou formulário.
    Se o layout principal mudar de modo incompatível, conserva a página atual.
    """
    cabecalho = re.search(r'<header class="header"[^>]*>.*?</header>', home, re.S)
    navegacao = re.search(r'<nav class="site-nav"[^>]*>.*?</nav>', home, re.S)
    rodape = re.search(r'<footer class="footer"[^>]*>.*?</footer>', home, re.S)
    if not all((cabecalho, navegacao, rodape)):
        return pagina
    # O CSS vem da fonte oficial do site. Mantemos a folha corporativa por último.
    estilos = re.findall(r'<style(?:\s[^>]*)?>.*?</style>', home, re.S | re.I)
    if not estilos:
        return pagina
    # Toda navegação interna deve apontar para a Home, não para #anchors da subpágina.
    cab = cabecalho.group(0)
    nav = navegacao.group(0)
    for ancora in ('inicio','produtos','servicos','quem-somos','contato','galeria','dicas-alphafest','novidades-alphafest'):
        cab = cab.replace('href="#'+ancora+'"','href="/#'+ancora+'"')
        nav = nav.replace('href="#'+ancora+'"','href="/#'+ancora+'"')
    # A busca da Home é controlada pelo script da Home. Na página interna,
    # conduza a pesquisa ao catálogo, não exiba um botão sem ação.
    nav = re.sub(r'<button\b[^>]*data-site-scroll="([^"]+)"[^>]*>(.*?)</button>',
                 lambda m: '<a href="/#'+html.escape(m.group(1), quote=True)+'">'+m.group(2)+'</a>',
                 nav, flags=re.S)
    cab = re.sub(r'<button\b[^>]*data-site-scroll="([^"]+)"[^>]*>(.*?)</button>',
                 lambda m: '<a href="/#'+html.escape(m.group(1), quote=True)+'">'+m.group(2)+'</a>',
                 cab, flags=re.S)
    # Fallback para procura: campo de busca abre a seção Produtos da Home.
    cab = re.sub(r'<form\b[^>]*class="([^"]*search[^"]*)"[^>]*>',
                 lambda m: m.group(0) if 'action=' in m.group(0) else m.group(0)[:-1]+' action="/" method="get">', cab)
    cab = re.sub(r'(<input\b(?=[^>]*type="search")[^>]*)(>)',
                 lambda m: m.group(1) + (' name="busca"' if 'name=' not in m.group(1) else '') + m.group(2), cab)
    # O logotipo já aparece na barra superior oficial. Evita duplicação na faixa interna.
    pagina = re.sub(r'<div class="corp-head">.*?</div>', '', pagina, count=1, flags=re.S)
    # Home shell encapsulado fora da seção interna.
    pagina = pagina.replace('<header class="corp-hero">', cab+nav+'<header class="corp-hero">', 1)
    pagina = pagina.replace('<footer class="corp-simple-footer">AlphaFest · Estamos presentes em cada presente!</footer>', rodape.group(0), 1)
    # Importante: colocar CSS oficial ANTES do CSS corporativo para manter o formulário.
    pagina = pagina.replace('<style>', '\n'.join(estilos)+'<style>', 1)
    # Em dispositivos móveis, subpágina não deve exibir a barra de WhatsApp flutuante
    # copiada da Home; o formulário corporativo já possui CTA próprio.
    return pagina
