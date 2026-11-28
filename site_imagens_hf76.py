"""HF76: extrai imagens embutidas de tags img para assets estaticos.

Nao modifica a imagem original, nao altera cadastro e nao publica. Escopo
intencionalmente restrito a src de <img>, preservando URLs de scripts, CSS e
dados de JSON fora de atributos de imagem.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import re
from typing import Dict, Tuple

# Apenas formatos que o navegador e o publicador atual aceitam como imagem.
TIPOS = {"png": "png", "jpeg": "jpg", "jpg": "jpg", "webp": "webp",
         "gif": "gif", "avif": "avif"}
IMG_SRC = re.compile(
    r"(<img\\b[^>]*?\\bsrc\\s*=\\s*[\"'])(data:image/([a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=]+))([\"'])",
    re.IGNORECASE | re.DOTALL,
)


def extrair_imagens_inline_hf76(html: str) -> Tuple[str, Dict[str, bytes]]:
    """Retorna HTML e mapa assets/img/<sha>.<ext> -> bytes.

    Reusa um mesmo arquivo quando a mesma imagem aparece repetidamente.
    Imagens invalidas permanecem intactas, sem substituir dados incompletos.
    """
    arquivos: Dict[str, bytes] = {}
    def substituir(match: re.Match) -> str:
        inicio, uri, tipo, texto, aspas = match.groups()
        extensao = TIPOS.get(tipo.lower())
        if not extensao:
            return match.group(0)
        try:
            bruto = base64.b64decode(texto, validate=True)
        except (ValueError, binascii.Error):
            return match.group(0)
        if not bruto:
            return match.group(0)
        digest = hashlib.sha256(bruto).hexdigest()[:24]
        caminho = f"assets/img/{digest}.{extensao}"
        arquivos[caminho] = bruto
        return inicio + "/" + caminho + aspas
    return IMG_SRC.sub(substituir, str(html or "")), arquivos
