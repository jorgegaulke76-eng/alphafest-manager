"""Pacote público de produção do novo site AlphaFest (HF44).

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
    """Acrescenta metadados públicos sem inserir qualquer marca de homologação."""
    pagina = str(html_site or "")
    metas = (
        '<meta name="robots" content="index,follow,max-image-preview:large">'
        '<meta name="googlebot" content="index,follow,max-image-preview:large">'
        f'<link rel="canonical" href="https://{DOMINIO_FINAL}/">'
        '<meta name="description" content="AlphaFest Itatiba: personalizados, balões, gráfica rápida, brindes, impressão 3D, gravação a laser e soluções sob medida para festas, presentes e marcas.">' 
    )
    if "<head>" in pagina:
        pagina = pagina.replace("<head>", "<head>" + metas, 1)
    elif "<head " in pagina:
        pos = pagina.find(">", pagina.find("<head "))
        if pos >= 0:
            pagina = pagina[: pos + 1] + metas + pagina[pos + 1 :]

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
    versao_manager: str = "20.4.9-I8.13.5-HF44",
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
    readme = f"""ALPHAFEST — PACOTE DE PRODUÇÃO HF44

Destino: Worker {PROJETO_WORKER}
Domínio principal: https://{DOMINIO_FINAL}
Hospedagem: {HOSPEDAGEM}

O QUE MUDA NESTE PACOTE
- Remove qualquer faixa/marca de homologação.
- Libera indexação pública (robots + meta robots).
- Inclui canonical e sitemap do domínio oficial.
- Mantém a mesma Fonte Única do Catálogo e os CTAs/WhatsApp homologados.
- Organiza os filtros públicos por categorias comerciais calculadas a partir do Catálogo oficial.
- Compatível com a publicação assistida HF44 pelo próprio Manager.

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
