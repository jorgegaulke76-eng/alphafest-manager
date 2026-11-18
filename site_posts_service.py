"""HF65.24.18 — Mural comercial AlphaFest: artes prontas, sem publicação automática.

Conteúdo separado da Galeria, Dicas, Campanha Destaque e Catálogo. Apenas
registros explicitamente aprovados são empacotados no site público.
"""
from __future__ import annotations
import html
import math
import re
import unicodedata
from datetime import date
from urllib.parse import quote

CATEGORIES = ['Natal', 'Black Friday', 'Brindes para empresas', 'Formaturas',
              'Balões', 'Festas e personalizados', 'Impressão 3D',
              'Gráfica rápida', 'Datas especiais', 'Outros']


def normalize(posts):
    if not isinstance(posts, list):
        return []
    out, seen = [], set()
    for p in posts[:1000]:
        if not isinstance(p, dict):
            continue
        post_id = re.sub(r'[^a-zA-Z0-9_-]', '', str(p.get('id', '')))[:64]
        if not post_id or post_id in seen:
            continue
        seen.add(post_id)
        out.append({
            'id': post_id,
            'title': str(p.get('title') or '').strip()[:140],
            'description': str(p.get('description') or '').strip()[:600],
            'category': str(p.get('category') or 'Outros').strip()[:70],
            'image_data_uri': str(p.get('image_data_uri') or ''),
            'status': 'publicado' if p.get('status') == 'publicado' else 'rascunho',
            'created_at': str(p.get('created_at') or '')[:20],
            'expires_at': str(p.get('expires_at') or '')[:10],
            'featured': bool(p.get('featured')),
        })
    return out


def published(posts, today=None):
    today = today or date.today()
    visible = []
    for p in normalize(posts):
        if p['status'] != 'publicado' or not p['image_data_uri'].startswith('data:image/'):
            continue
        try:
            if p['expires_at'] and date.fromisoformat(p['expires_at']) < today:
                continue
        except ValueError:
            continue
        visible.append(p)
    return sorted(visible, key=lambda p: (p['featured'], p['created_at'], p['id']), reverse=True)


def safe(value):
    return html.escape(str(value or ''), quote=True)


def whatsapp(number, title):
    number = re.sub(r'\D', '', str(number or ''))
    if number and not number.startswith('55'):
        number = '55' + number
    if not number:
        return '/#contato'
    return 'https://wa.me/' + number + '?text=' + quote('Olá! Vi a publicação "' + title + '" no site da AlphaFest e gostaria de saber mais.')


def _card(p, number):
    # A arte já é a publicidade: somente imagem inteira e CTA WhatsApp.
    # Título fica exclusivamente para organização interna e texto da mensagem.
    label = p['title'] or 'arte AlphaFest'
    url = safe(whatsapp(number, label))
    return ('<article class="afposts-card">'
            '<a class="afposts-img" href="' + url + '" target="_blank" rel="noopener noreferrer" aria-label="Pedir arte pelo WhatsApp">'
            '<img loading="lazy" decoding="async" src="' + safe(p['image_data_uri']) + '" alt="' + safe(label) + '"></a>'
            '<div class="afposts-info"><a class="afposts-cta" target="_blank" rel="noopener noreferrer" href="' + url + '">💬 Quero este</a></div>'
            '</article>')


CSS = '''
.afposts-container{max-width:1240px;margin:auto;padding:0 22px}.afposts-section{padding:56px 0;background:#f5fbff}
.afposts-head{display:flex;align-items:flex-end;justify-content:space-between;gap:18px;flex-wrap:wrap;margin-bottom:22px}
.afposts-head h2{color:#073d72;font-size:clamp(24px,3vw,34px);margin:7px 0}.afposts-head p{color:#526b81;margin:0}
.afposts-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}
.afposts-card{background:#fff;border:1px solid #dceaf7;border-radius:16px;overflow:hidden;box-shadow:0 8px 24px #143d5910;min-width:0}
.afposts-img{display:block;padding:10px;background:white;text-align:center}.afposts-img img{width:100%;height:auto;max-height:390px;object-fit:contain;display:block;margin:auto}
.afposts-info{padding:0 12px 14px;text-align:center}.afposts-info span{font-size:11px;font-weight:800;color:#087ab8;text-transform:uppercase}
.afposts-info h3{font-size:16px;margin:5px 0 9px;color:#103a60}.afposts-info p{font-size:13px;color:#567085;line-height:1.5}
.afposts-cta{display:block;background:#075eaa;color:#fff!important;border-radius:10px;padding:10px 12px;font-size:12px;font-weight:800;text-decoration:none;margin-top:6px}
.afposts-all{display:inline-block;padding:11px 17px;border:1px solid #087cc0;border-radius:10px;color:#06649e;font-weight:850;text-decoration:none}
@media(max-width:900px){.afposts-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:540px){.afposts-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.afposts-img img{max-height:250px}.afposts-info{padding:10px}.afposts-info h3{font-size:14px}.afposts-cta{font-size:11px;padding:9px}.afposts-section{padding:34px 0}}
'''


def inject_home(site_html, posts, number='', preview=False):
    page = str(site_html or '')
    if 'id="novidades-alphafest"' in page:
        return page
    items = published(posts)
    if preview and not items:
        inner = '<p>Sem publicações aprovadas. Cadastre as artes no Manager e selecione “Aprovado”.</p>'
    elif not items:
        return page
    else:
        inner = '<div class="afposts-grid">' + ''.join(_card(p, number) for p in items[:8]) + '</div>'
    section = ('<section id="novidades-alphafest" class="afposts-section"><div class="afposts-container">'
               '<div class="afposts-head"><div><strong style="color:#097fc5">ALPHAFEST · NOVIDADES</strong>'
               '<h2>Novidades &amp; Ofertas</h2><p>Nossas campanhas, lançamentos e ideias para presentear.</p></div>'
               '<a class="afposts-all" href="/novidades/">Ver todas as publicações</a></div>' + inner + '</div></section>')
    marker = '<footer class="footer">'
    # Colocar após Dicas quando presente, preservando a navegação e os demais blocos.
    if marker in page:
        page = page.replace(marker, section + marker, 1)
    elif '</body>' in page:
        page = page.replace('</body>', section + '</body>', 1)
    page = page.replace('</head>', '<style id="afposts-style">' + CSS + '</style></head>', 1)
    return page


def archive_pages(posts, number=''):
    items = published(posts)
    if not items:
        return {}
    result = {}
    per_page = 24
    pages = math.ceil(len(items) / per_page)
    for i in range(pages):
        subset = items[i*per_page:(i+1)*per_page]
        cards = ''.join(_card(p, number) for p in subset)
        # Páginas estáticas distintas, sem query-string dependente do Worker.
        prev_link = ('<a href="/novidades/' + ('pagina-'+str(i+1)+'/' if i>1 else '') + '">← Anterior</a>' if i>0 else '')
        next_link = ('<a href="/novidades/pagina-' + str(i+2) + '/">Próxima →</a>' if i+1<pages else '')
        pagination = '<nav class="afposts-pages">' + prev_link + '<span>Página ' + str(i+1) + ' de ' + str(pages) + '</span>' + next_link + '</nav>'
        body = ('''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="index,follow"><title>Novidades &amp; Ofertas | AlphaFest</title><meta name="description" content="Campanhas, lançamentos e novidades da AlphaFest em Itatiba"><link rel="icon" href="/favicon.ico"><style>body{font-family:Arial,sans-serif;background:#f5fbff;margin:0;color:#123a5b}header{background:#075da5;color:white;padding:22px max(20px,calc((100vw - 1240px)/2))}header a{color:white;text-decoration:none;font-weight:800}.afposts-pages{display:flex;justify-content:space-between;gap:14px;padding:28px 0}.afposts-pages a{color:#075da5;font-weight:800}footer{padding:30px;text-align:center;background:#fff}</style><style>''' + CSS + '''</style></head><body><header><a href="/">AlphaFest</a> · Novidades &amp; Ofertas</header><main class="afposts-section"><div class="afposts-container"><div class="afposts-head"><div><h1>Novidades &amp; Ofertas</h1><p>Confira nossas artes, campanhas e produtos personalizados.</p></div><a class="afposts-all" href="/">Voltar à loja</a></div><div class="afposts-grid">''' + cards + '''</div>''' + pagination + '''</div></main><footer>AlphaFest · Itatiba/SP · <a href="/">Site oficial</a></footer></body></html>''')
        endereco = 'https://alphafest.com.br/novidades/' + (f'pagina-{i+1}/' if i else '')
        titulo_seo = 'Novidades e ofertas da AlphaFest em Itatiba' + (f' — página {i+1}' if i else '')
        descricao_seo = 'Veja campanhas e artes de produtos personalizados, balões e presentes da AlphaFest em Itatiba. Consulte pelo WhatsApp.'
        from html import escape as _escape_seo
        from json import dumps as _dumps_seo
        complemento = (
            f'<link rel="canonical" href="{_escape_seo(endereco, quote=True)}">'
            f'<meta property="og:type" content="website">'
            f'<meta property="og:locale" content="pt_BR">'
            f'<meta property="og:title" content="{_escape_seo(titulo_seo, quote=True)}">'
            f'<meta property="og:description" content="{_escape_seo(descricao_seo, quote=True)}">'
            f'<meta property="og:url" content="{_escape_seo(endereco, quote=True)}">'
            f'<meta name="twitter:card" content="summary">'
        )
        trilha = {'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':[
            {'@type':'ListItem','position':1,'name':'AlphaFest','item':'https://alphafest.com.br/'},
            {'@type':'ListItem','position':2,'name':'Novidades e Ofertas','item':'https://alphafest.com.br/novidades/'},
        ]}
        complemento += '<script type="application/ld+json">'+_dumps_seo(trilha,ensure_ascii=False,separators=(',',':'))+'</script>'
        body = body.replace('</head>', complemento+'</head>', 1)
        body = body.replace('<title>Novidades &amp; Ofertas | AlphaFest</title>',
                            '<title>'+_escape_seo(titulo_seo)+'</title>', 1)
        result['novidades/index.html' if i==0 else f'novidades/pagina-{i+1}/index.html'] = body
    return result
