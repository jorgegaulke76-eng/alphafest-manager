"""Pacote público de produção do site AlphaFest (motor HF44 · HF51.4 · visual HF48.3-HF4).

Gera um snapshot estático pronto para o Worker já homologado. Não altera DNS,
não cria Custom Domain e não modifica dados operacionais do Manager.
"""
from __future__ import annotations
from site_metrics_service import inject_tracking

import io
import json
import re
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict

from site_adsense_service import inserir_meta_adsense, gerar_ads_txt, normalizar_publisher_id
from site_dicas_multicanal_service import paginas_dicas
from site_posts_service import archive_pages
from site_corporativo_service import corporate_page
from site_favicon_service import favicon_assets, with_favicon
from site_pwa_service import inject_pwa, pwa_assets
from site_whatsapp_context_service import inject_whatsapp_context
from site_institucional_adsense_service import paginas_institucionais

def _rastreador_pagina_interna(pagina: str, home: str) -> str:
    """Injeta o rastreador; se os Secrets não estiverem visíveis nessa etapa,
    reutiliza o script público já presente na Home, sem expor chaves privadas.
    """
    pagina = inject_tracking(pagina)
    if 'id="alphafest-site-metrics"' in pagina:
        return pagina
    existente = re.search(r'<script id="alphafest-site-metrics">.*?</script>', home, re.S)
    if not existente:
        return pagina
    return pagina.replace('</body>', existente.group(0)+'</body>', 1) if '</body>' in pagina else pagina+existente.group(0)


DOMINIO_FINAL = "alphafest.com.br"
PROJETO_WORKER = "alphafest-novo"
HOSPEDAGEM = "Cloudflare Workers · Static Assets"


def preparar_html_producao(html_site: str) -> str:
    """Acrescenta metadados públicos, SEO social e dicas de performance sem alterar o visual."""
    pagina = str(html_site or "")

    metas = []
    if 'name="robots"' not in pagina:
        metas.append('<meta name="robots" content="index,follow,max-image-preview:large">')
    if 'name="googlebot"' not in pagina:
        metas.append('<meta name="googlebot" content="index,follow,max-image-preview:large">')
    if 'rel="canonical"' not in pagina:
        metas.append(f'<link rel="canonical" href="https://{DOMINIO_FINAL}/">')
    if 'name="description"' not in pagina:
        metas.append('<meta name="description" content="AlphaFest Itatiba: personalizados, balões, gráfica rápida, brindes, impressão 3D, gravação a laser e soluções sob medida para festas, presentes e marcas.">')
    if 'property="og:url"' not in pagina:
        metas.append(f'<meta property="og:url" content="https://{DOMINIO_FINAL}/">')
    if 'property="og:locale"' not in pagina:
        metas.append('<meta property="og:locale" content="pt_BR">')
    if 'name="format-detection"' not in pagina:
        metas.append('<meta name="format-detection" content="telephone=no">')
    if 'rel="dns-prefetch" href="https://wa.me"' not in pagina:
        metas.append('<link rel="dns-prefetch" href="https://wa.me">')
    if 'name="theme-color"' not in pagina:
        metas.append('<meta name="theme-color" content="#0796e8">')
    if 'name="application-name"' not in pagina:
        metas.append('<meta name="application-name" content="AlphaFest">')
    if 'name="author"' not in pagina:
        metas.append('<meta name="author" content="AlphaFest Itatiba">')

    # HF51.5 — dados estruturados sem impacto visual. Ajuda buscadores a entenderem
    # a marca e o site oficial sem inventar endereço, telefone ou horário comercial.
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "@id": f"https://{DOMINIO_FINAL}/#organization",
                "name": "AlphaFest",
                "alternateName": "AlphaFest Itatiba",
                "url": f"https://{DOMINIO_FINAL}/",
                "description": "Personalizados, balões, gráfica rápida, brindes, impressão 3D, gravação a laser e soluções sob medida para festas, presentes e marcas.",
            },
            {
                "@type": "WebSite",
                "@id": f"https://{DOMINIO_FINAL}/#website",
                "url": f"https://{DOMINIO_FINAL}/",
                "name": "AlphaFest",
                "inLanguage": "pt-BR",
                "publisher": {"@id": f"https://{DOMINIO_FINAL}/#organization"},
            },
        ],
    }
    schema_tag = '<script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False, separators=(",", ":")) + '</script>'
    if 'id="alphafest-structured-data"' not in pagina and '"@id":"https://alphafest.com.br/#organization"' not in pagina:
        schema_tag = schema_tag.replace('<script ', '<script id="alphafest-structured-data" ', 1)
        metas.append(schema_tag)

    bloco = ''.join(metas)
    if bloco:
        if "<head>" in pagina:
            pagina = pagina.replace("<head>", "<head>" + bloco, 1)
        elif "<head " in pagina:
            pos = pagina.find(">", pagina.find("<head "))
            if pos >= 0:
                pagina = pagina[: pos + 1] + bloco + pagina[pos + 1 :]

    # Imagens abaixo da dobra: decodificação assíncrona reduz bloqueio de renderização.
    # Não altera o visual e preserva imagens críticas que já usam loading=eager.
    pagina = pagina.replace('loading="lazy"', 'loading="lazy" decoding="async"')
    pagina = pagina.replace('decoding="async" decoding="async"', 'decoding="async"')

    # Blindagem: um pacote de produção nunca deve carregar marcas do staging.
    proibidos = (
        "SITE PARALELO HF40",
        "HOMOLOGAÇÃO",
        "NÃO PUBLICADO EM ALPHAFEST.COM.BR",
        "noindex,nofollow,noarchive",
    )
    for termo in proibidos:
        if termo in pagina:
            raise ValueError(f"HTML de produção contém marcador de staging: {termo}")
    return pagina


def resumo_producao(*, total_produtos: int = 0) -> Dict[str, Any]:
    return {
        "dominio_final": DOMINIO_FINAL,
        "projeto_worker": PROJETO_WORKER,
        "hospedagem": HOSPEDAGEM,
        "zona_cloudflare": "Active",
        "dns_cloudflare": True,
        "dominio_raiz_conectado": True,
        "www": "301 → alphafest.com.br",
        "indexacao": "Liberada no pacote de produção",
        "produtos_snapshot": int(total_produtos or 0),
        "rollback": "Preservado",
    }


def gerar_pacote_producao(
    html_site: str,
    *,
    total_produtos: int = 0,
    versao_manager: str = "20.4.9-I8.13.5-HF51.4",
    adsense_publisher_id: str = "",
    dicas_content: Any = None,
    dicas_whatsapp: str = "",
    posts_content: Any = None,
    corporate_products: Any = None,
    corporate_logo_src: str = '',
    corporate_image_resolver: Any = None,
) -> bytes:
    """Gera ZIP para New deployment no Worker alphafest-novo.

    O ZIP não contém comandos de DNS. A conexão do domínio é externa e manual.
    """
    html_publico = inject_pwa(inject_whatsapp_context(with_favicon(preparar_html_producao(html_site))))
    adsense_id = normalizar_publisher_id(adsense_publisher_id)
    html_publico = inserir_meta_adsense(html_publico, adsense_id)
    status = resumo_producao(total_produtos=total_produtos)
    status["adsense_metatag_incluida"] = bool(adsense_id)
    status["adsense_anuncios_ativados"] = False
    status.update({
        "versao_manager": versao_manager,
        "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
    })

    robots = f"User-agent: *\nAllow: /\nSitemap: https://{DOMINIO_FINAL}/sitemap.xml\n"
    hoje = datetime.now(timezone.utc).date().isoformat()
    paginas = paginas_dicas(dicas_content or [], whatsapp=dicas_whatsapp)
    paginas.update(paginas_institucionais())
    paginas.update(archive_pages(posts_content or [], number=dicas_whatsapp))
    paginas["empresas/index.html"] = _rastreador_pagina_interna(corporate_page({"whatsapp_catalogo": dicas_whatsapp}, produtos=corporate_products, imagem_resolver=corporate_image_resolver, logo_src=corporate_logo_src, site_shell_html=html_publico), html_publico)
    # Todas as rotas realmente geradas entram no sitemap, sem URLs inventadas.
    # Os caminhos de paginação ficam individuais para indexação independente.
    urls_publicas = sorted({url[:-10] if url.endswith('index.html') else url for url in paginas})
    urls_dicas = ''.join(
        f'  <url><loc>https://{DOMINIO_FINAL}/{url}</loc><lastmod>{hoje}</lastmod></url>\n'
        for url in urls_publicas
    )
    sitemap = f'''<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n  <url>\n    <loc>https://{DOMINIO_FINAL}/</loc>\n    <lastmod>{hoje}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>1.0</priority>\n  </url>\n{urls_dicas}</urlset>\n'''
    headers = """/sw.js
  Cache-Control: no-cache, no-store, must-revalidate
/manifest.webmanifest
  Cache-Control: no-cache, no-store, must-revalidate
/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  X-Frame-Options: SAMEORIGIN
"""
    readme = f"""ALPHAFEST — PACOTE DE PRODUÇÃO HF51.5

Destino: Worker {PROJETO_WORKER}
Domínio principal: https://{DOMINIO_FINAL}
Hospedagem: {HOSPEDAGEM}

O QUE MUDA NESTE PACOTE
- Remove qualquer faixa/marca de homologação.
- Libera indexação pública (robots + meta robots).
- Inclui canonical e sitemap do domínio oficial.
- Mantém a mesma Fonte Única do Catálogo e os CTAs/WhatsApp homologados.
- Publica o HF51.5 · acabamento técnico final sem alterar o visual aprovado: metadados sociais, canonical, indexação, lazy loading/decodificação assíncrona e renderização eficiente dos cards.
- Inclui a Galeria autorizada/pré-selecionada, com filtros por Categoria, Subcategoria e Tema.
- Liga automaticamente cada produto aos trabalhos reais já selecionados na Galeria, sem novo cadastro.
- O carrossel usa o controle CarrosselSite do mesmo Catálogo; sem seleção, usa Destaques apenas como fallback visual.
- Organiza Produtos por Categoria → Subcategoria sem duplicar cadastro.
- Continua compatível com o motor seguro de publicação assistida HF44 pelo próprio Manager.

PUBLICAÇÃO
1. Preferencial: usar **Publicar site agora** no Manager (HF44).
2. Alternativa/rollback: Cloudflare > Workers & Pages > {PROJETO_WORKER} > New deployment > Upload static files.
3. Enviar este ZIP.
4. Confirmar https://{DOMINIO_FINAL} em desktop e celular.
5. O www já redireciona em 301 para o domínio principal.

SEGURANÇA
Este pacote NÃO altera DNS, nameservers, MX, webmail ou Custom Domains.
O rollback do DNS anterior continua documentado no kit HF41.
"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("index.html", html_publico)
        for _favicon_path, _favicon_bytes in favicon_assets().items():
            zf.writestr(_favicon_path, _favicon_bytes)
        for _pwa_path, _pwa_bytes in pwa_assets().items():
            zf.writestr(_pwa_path, _pwa_bytes)
        zf.writestr("404.html", html_publico)
        zf.writestr("robots.txt", robots)
        zf.writestr("sitemap.xml", sitemap)
        # HF65.22 — publicacoes editoriais sao paginas estaticas opcionais.
        paginas = paginas_dicas(dicas_content or [], whatsapp=dicas_whatsapp)
        paginas.update(paginas_institucionais())
        paginas.update(archive_pages(posts_content or [], number=dicas_whatsapp))
        paginas["empresas/index.html"] = _rastreador_pagina_interna(corporate_page({"whatsapp_catalogo": dicas_whatsapp}, produtos=corporate_products, imagem_resolver=corporate_image_resolver, logo_src=corporate_logo_src, site_shell_html=html_publico), html_publico)
        for caminho, conteudo in sorted(paginas.items()):
            zf.writestr(caminho, inject_pwa(inject_whatsapp_context(with_favicon(conteudo))))
        if adsense_id:
            zf.writestr("ads.txt", gerar_ads_txt(adsense_id))
        zf.writestr("_headers", headers)
        zf.writestr("README-PRODUCAO.txt", readme)
        zf.writestr("STATUS-PRODUCAO.json", json.dumps(status, ensure_ascii=False, indent=2))
    return buffer.getvalue()
