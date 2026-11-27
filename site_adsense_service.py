"""Verificação opcional do Google AdSense no site AlphaFest (HF65.20).

Somente a metatag de titularidade e o arquivo ads.txt são publicados. Nenhum
script de anúncio ou bloco publicitário é ativado nesta etapa.
"""
from __future__ import annotations

import re
from typing import Any, Dict

DEFAULT_ADSENSE_CONFIG: Dict[str, str] = {"publisher_id": ""}
_PUBLISHER = re.compile(r"ca-pub-(\d{16})")


def normalizar_publisher_id(valor: Any) -> str:
    """Aceita ID ca-pub ou metatag oficial colada pelo usuário; rejeita ambiguidades."""
    bruto = str(valor or "").strip()
    if not bruto:
        return ""
    # A entrada pode ser o código inteiro copiado da tela de verificação.
    encontrados = set(_PUBLISHER.findall(bruto))
    if len(encontrados) != 1:
        raise ValueError(
            "Informe o ID válido ca-pub- seguido de 16 dígitos, ou cole a metatag do AdSense."
        )
    return "ca-pub-" + encontrados.pop()


def normalize_adsense_config(value: Any) -> Dict[str, str]:
    if not isinstance(value, dict):
        return dict(DEFAULT_ADSENSE_CONFIG)
    return {"publisher_id": normalizar_publisher_id(value.get("publisher_id", ""))}


def inserir_meta_adsense(html_site: str, publisher_id: str) -> str:
    """Insere metatag de verificação no head sem duplicar tags em republicações."""
    pagina = str(html_site or "")
    ident = normalizar_publisher_id(publisher_id)
    if not ident:
        return pagina
    # Remover somente metatags com o nome específico, preservando SEO do Manager.
    pagina = re.sub(
        r"<meta\b(?=[^>]*\bname\s*=\s*['\"]google-adsense-account['\"])[^>]*>\s*",
        "",
        pagina,
        flags=re.IGNORECASE,
    )
    head = re.search(r"<head(?:\s[^>]*)?>", pagina, flags=re.IGNORECASE)
    if not head:
        raise ValueError("O HTML do site não contém <head>; verificação AdSense não inserida.")
    tag = f'<meta name="google-adsense-account" content="{ident}">'
    return pagina[:head.end()] + tag + pagina[head.end():]


def gerar_ads_txt(publisher_id: str) -> str:
    """Linha padrão do Google para ads.txt (não ativa exibição de anúncios)."""
    ident = normalizar_publisher_id(publisher_id)
    if not ident:
        return ""
    return f"google.com, {ident[3:]}, DIRECT, f08c47fec0942fa0\n"
