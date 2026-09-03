"""Pacote de homologação paralelo do novo site AlphaFest (HF39).

O staging é um snapshot somente leitura da mesma vitrine gerada pelo Catálogo
oficial. Não publica, não altera DNS e não cria CNAME para alphafest.com.br.
"""
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict

DOMINIO_FINAL = "alphafest.com.br"
HOSPEDAGEM_STAGING = "Cloudflare Pages"


def preparar_html_staging(html_site: str, *, versao: str = "HF39") -> str:
    """Transforma o HTML público em cópia de homologação não indexável."""
    pagina = str(html_site or "")
    meta = (
        '<meta name="robots" content="noindex,nofollow,noarchive">'
        '<meta name="googlebot" content="noindex,nofollow,noarchive">'
    )
    if "<head>" in pagina:
        pagina = pagina.replace("<head>", "<head>" + meta, 1)
    elif "<head " in pagina:
        pos = pagina.find(">", pagina.find("<head "))
        if pos >= 0:
            pagina = pagina[: pos + 1] + meta + pagina[pos + 1 :]

    aviso = (
        f'<div class="staging-hf39" style="background:#17243a;color:#fff;text-align:center;'
        'font:800 11px/1.35 Arial,sans-serif;letter-spacing:.06em;padding:8px 12px">'
        f'SITE PARALELO {versao} · HOMOLOGAÇÃO · NÃO PUBLICADO EM {DOMINIO_FINAL.upper()}</div>'
    )
    if "<body>" in pagina:
        pagina = pagina.replace("<body>", "<body>" + aviso, 1)
    return pagina


def resumo_staging(*, total_produtos: int = 0) -> Dict[str, Any]:
    return {
        "site_atual": "Protegido / continua online",
        "dominio_final": DOMINIO_FINAL,
        "hospedagem_planejada": HOSPEDAGEM_STAGING,
        "dns_alterado": False,
        "publicado_dominio_final": False,
        "indexacao": "Bloqueada no staging",
        "produtos_snapshot": int(total_produtos or 0),
    }


def gerar_pacote_staging(
    html_site: str,
    *,
    total_produtos: int = 0,
    versao_manager: str = "20.4.9-I8.13.5-HF39",
) -> bytes:
    """Gera ZIP estático pronto para teste em Cloudflare Pages.

    O pacote propositalmente NÃO contém CNAME nem instruções executáveis de DNS.
    A troca de alphafest.com.br fica para a etapa final, manual e reversível.
    """
    html_staging = preparar_html_staging(html_site, versao="HF39")
    status = resumo_staging(total_produtos=total_produtos)
    status.update({
        "versao_manager": versao_manager,
        "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
    })

    robots = "User-agent: *\nDisallow: /\n"
    headers = """/*
  X-Robots-Tag: noindex, nofollow, noarchive
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
"""
    readme = f"""ALPHAFEST — SITE PARALELO / STAGING HF39

OBJETIVO
Testar o novo site em paralelo sem alterar o site atual nem o domínio {DOMINIO_FINAL}.

ARQUIVOS
- index.html: novo site/vitrine gerado do Catálogo oficial do Manager.
- 404.html: fallback estático.
- robots.txt + _headers: bloqueiam indexação durante a homologação.
- STATUS-STAGING.json: registra o estado seguro do pacote.
- CHECKLIST-VIRADA-DOMINIO.txt: roteiro futuro; NÃO executa nenhuma alteração.

HOSPEDAGEM PLANEJADA
{HOSPEDAGEM_STAGING} em endereço temporário *.pages.dev durante a homologação.

IMPORTANTE
Este pacote NÃO contém CNAME, não muda DNS e não assume {DOMINIO_FINAL}.
O site atual deve permanecer online até a aprovação final.
"""
    checklist = f"""CHECKLIST FUTURO — VIRADA DO DOMÍNIO {DOMINIO_FINAL}

[ ] 1. Homologar o site paralelo em desktop e celular.
[ ] 2. Conferir produtos, fotos, textos, WhatsApp e páginas institucionais.
[ ] 3. Reaproveitar somente o conteúdo aprovado do site antigo.
[ ] 4. Fazer backup das configurações DNS atuais antes de qualquer mudança.
[ ] 5. Adicionar o domínio à nova hospedagem somente na janela de virada.
[ ] 6. Alterar DNS apenas após confirmação de que o novo site está pronto.
[ ] 7. Confirmar HTTPS e redirecionamento entre www e domínio principal.
[ ] 8. Testar {DOMINIO_FINAL} em computador e celular.
[ ] 9. Manter possibilidade de rollback para os registros DNS anteriores.
[ ] 10. Só depois retirar/desativar a hospedagem antiga.

A HF39 NÃO executa nenhum item deste checklist automaticamente.
"""
    deploy = """STAGING EM CLOUDFLARE PAGES — ROTEIRO DE HOMOLOGAÇÃO

1. Criar um projeto Pages separado para o novo site AlphaFest.
2. Fazer upload/deploy deste pacote estático.
3. Usar o endereço temporário fornecido em *.pages.dev.
4. NÃO adicionar alphafest.com.br como domínio personalizado nesta fase.
5. Conferir a homologação pelo endereço temporário.
6. A conexão do domínio oficial fica reservada para a virada final.

O staging contém noindex em HTML, robots.txt e _headers para reduzir o risco de indexação.
"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("index.html", html_staging)
        zf.writestr("404.html", html_staging)
        zf.writestr("robots.txt", robots)
        zf.writestr("_headers", headers)
        zf.writestr("README-STAGING.txt", readme)
        zf.writestr("DEPLOY-CLOUDFLARE-PAGES.txt", deploy)
        zf.writestr("CHECKLIST-VIRADA-DOMINIO.txt", checklist)
        zf.writestr("STATUS-STAGING.json", json.dumps(status, ensure_ascii=False, indent=2))
    return buffer.getvalue()
