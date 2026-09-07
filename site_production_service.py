"""Pacote público de produção do site AlphaFest (motor HF44 · HF51.4 · visual HF48.3-HF4).

Gera um snapshot estático pronto para o Worker já homologado. Não altera DNS,
não cria Custom Domain e não modifica dados operacionais do Manager.
"""
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict

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
) -> bytes:
    """Gera ZIP para New deployment no Worker alphafest-novo.

    O ZIP não contém comandos de DNS. A conexão do domínio é externa e manual.
    """
    html_publico = preparar_html_producao(html_site)
    status = resumo_producao(total_produtos=total_produtos)
    status.update({
        "versao_manager": versao_manager,
        "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
    })

    robots = f"User-agent: *\nAllow: /\nSitemap: https://{DOMINIO_FINAL}/sitemap.xml\n"
    sitemap = f'''<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n  <url><loc>https://{DOMINIO_FINAL}/</loc></url>\n</urlset>\n'''
    headers = """/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  X-Frame-Options: SAMEORIGIN
"""
    readme = f"""ALPHAFEST — PACOTE DE PRODUÇÃO HF51.4

Destino: Worker {PROJETO_WORKER}
Domínio principal: https://{DOMINIO_FINAL}
Hospedagem: {HOSPEDAGEM}

O QUE MUDA NESTE PACOTE
- Remove qualquer faixa/marca de homologação.
- Libera indexação pública (robots + meta robots).
- Inclui canonical e sitemap do domínio oficial.
- Mantém a mesma Fonte Única do Catálogo e os CTAs/WhatsApp homologados.
- Publica o HF51.4 · SEO + velocidade sem alterar o visual aprovado: metadados sociais, canonical, indexação, lazy loading/decodificação assíncrona e renderização eficiente dos cards.
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
        zf.writestr("404.html", html_publico)
        zf.writestr("robots.txt", robots)
        zf.writestr("sitemap.xml", sitemap)
        zf.writestr("_headers", headers)
        zf.writestr("README-PRODUCAO.txt", readme)
        zf.writestr("STATUS-PRODUCAO.json", json.dumps(status, ensure_ascii=False, indent=2))
    return buffer.getvalue()
