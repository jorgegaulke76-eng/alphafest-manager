"""HF80 - acessórios natalinos azuis para mascotes externos do pop-up.

O visual da campanha é sazonal e não altera os mascotes originais.
O SVG é leve, transparente e usa azul, branco, prata e dourado.
"""
from __future__ import annotations

import base64
import unicodedata
from typing import Any


_AZUL_NATAL_HAT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 330 215" fill="none">
<defs>
<linearGradient id="b" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#08B4FF"/><stop offset=".45" stop-color="#0058D8"/><stop offset="1" stop-color="#00318D"/></linearGradient>
<linearGradient id="w" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#FFF"/><stop offset="1" stop-color="#BDDFF6"/></linearGradient>
<filter id="s"><feGaussianBlur stdDeviation="2"/></filter>
</defs>
<path d="M46 130C38 77 71 41 122 26c42-12 89-15 128 8 24 15 42 36 58 29 11-5 19-12 19-12-9 34-36 61-78 51-48-12-89-8-131 11Z" fill="url(#b)" stroke="#0047B5" stroke-width="5"/>
<path d="M56 101C100 89 164 85 228 98" stroke="#78DAFF" stroke-width="7" stroke-linecap="round" opacity=".7"/>
<path d="M27 124C89 101 186 106 260 121c13 5 19 15 17 26-4 15-17 23-37 19-77-13-152-14-210 7-18 6-31-7-29-23 2-13 11-21 26-26Z" fill="url(#w)" stroke="#D5E7F7" stroke-width="3"/>
<path d="M17 144c76-20 150-21 247 3" stroke="#FFF" stroke-width="7" stroke-linecap="round" opacity=".8"/>
<circle cx="302" cy="66" r="27" fill="url(#w)" stroke="#C8E3FC" stroke-width="5"/><circle cx="297" cy="60" r="11" fill="#FFF" opacity=".9"/>
<path d="m107 36 6-12 6 12 13 2-10 9 3 13-12-7-12 7 2-13-10-9Z" fill="#FCE077" stroke="#D9A91C" stroke-width="2"/>
</svg>"""


def eh_natal_azul(config: Any) -> bool:
    """Aplica somente a campanha identificada explicitamente como Natal."""
    config = config if isinstance(config, dict) else {}
    valor = " ".join(str(config.get(c) or "") for c in ("campaign_name", "headline", "message", "image_src"))
    sem_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", valor.lower())
        if not unicodedata.combining(c)
    )
    return "natal" in sem_acentos


def natal_hat_data_uri() -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(_AZUL_NATAL_HAT.encode("utf-8")).decode("ascii")


def mascote_natal_html(nome: str, imagem_src: str, nome_escapado: str) -> str:
    """Envolve a arte oficial existente, sem mudar seu logo, com gorro natalino."""
    if not imagem_src:
        return ""
    if nome not in ("thu", "fox"):
        return ""
    from html import escape
    hat = natal_hat_data_uri()
    return (
        f'<div class="afc65-mascot afc65-{nome} afc65-mascot-natal" '
        f'role="img" aria-label="{escape(nome_escapado, quote=True)} com roupa natalina azul">'
        f'<img class="afc65-mascot-base" src="{escape(imagem_src, quote=True)}" alt="" aria-hidden="true">'
        f'<img class="afc65-natal-hat" src="{hat}" alt="" aria-hidden="true">'
        f'</div>'
    )


NATAL_CSS = """
.afc65-mascot-natal{overflow:visible}
.afc65-mascot-natal .afc65-mascot-base{display:block;width:100%;height:100%;object-fit:contain;object-position:bottom}
.afc65-mascot-natal .afc65-natal-hat{position:absolute;pointer-events:none;filter:drop-shadow(0 5px 6px rgba(0,44,108,.20));z-index:3}
.afc65-mascot-natal.afc65-thu{width:min(370px,31vw);height:min(66vh,610px)}
.afc65-mascot-natal.afc65-thu .afc65-natal-hat{width:82%;height:auto;top:-5%;left:7%;transform:rotate(-10deg)}
.afc65-mascot-natal.afc65-fox{width:min(350px,29vw);height:auto}
.afc65-mascot-natal.afc65-fox .afc65-mascot-base{height:auto}
.afc65-mascot-natal.afc65-fox .afc65-natal-hat{width:49%;height:auto;top:-14%;left:-5%;transform:rotate(-11deg)}
"""
