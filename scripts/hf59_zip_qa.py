"""HF59: valida o ZIP estatico REAL de producao, sem publica-lo.

Usa apenas quatro imagens SVG FICTICIAS geradas por hf59_visual_qa.
O ZIP com conteúdo fictício é construido EM MEMÓRIA e não fica disponível
para download/publicação acidental. Salva somente um relatorio de auditoria.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.hf59_visual_qa import escrever_site
from site_cloudflare_publish_service import (
    extrair_pacote_publico,
    fingerprint_pacote,
)
from site_production_service import gerar_pacote_producao, preparar_html_producao

OUT = ROOT / "artifacts" / "hf59_visual"


def avaliar_pacote() -> dict:
    if any(os.getenv(x) for x in (
        "CLOUDFLARE_API_TOKEN", "SUPABASE_SERVICE_KEY", "SUPABASE_SERVICE_ROLE_KEY",
    )):
        raise AssertionError("A auditoria fictícia do ZIP nunca deve usar credenciais de produção.")

    origem = escrever_site()
    html_antes = origem.read_text(encoding="utf-8")
    assert html_antes.count("O carinho dos nossos clientes") == 1
    assert html_antes.count('class="hf6514-testimonial-zoom"') == 4
    assert "Texto redundante de QA" not in html_antes

    # Chama EXATAMENTE o motor de pacote usado pelo Manager, mas não salva nem
    # transmite o ZIP. A função de deploy Cloudflare não é utilizada.
    pacote = gerar_pacote_producao(
        html_antes, total_produtos=0, versao_manager="HF59-REVIEW-FICTICIO",
        adsense_publisher_id="", dicas_content=[], posts_content=[],
    )
    assert pacote.startswith(b"PK"), "O gerador não retornou um arquivo ZIP."

    obrigatorios = {
        "index.html", "404.html", "robots.txt", "sitemap.xml",
        "_headers", "README-PRODUCAO.txt", "STATUS-PRODUCAO.json",
        "manifest.webmanifest", "sw.js",
    }

    with zipfile.ZipFile(io.BytesIO(pacote), "r") as zf:
        assert zf.testzip() is None, "O ZIP contém arquivo danificado."
        nomes = set(zf.namelist())
        assert obrigatorios.issubset(nomes), "Arquivos exigidos ausentes: " + repr(obrigatorios - nomes)
        index_bytes = zf.read("index.html")
        index = index_bytes.decode("utf-8")
        status = json.loads(zf.read("STATUS-PRODUCAO.json").decode("utf-8"))
        assert status["versao_manager"] == "HF59-REVIEW-FICTICIO"
        assert status["dominio_final"] == "alphafest.com.br"
        assert "O carinho dos nossos clientes" in index
        assert index.count("Cada mensagem que recebemos") == 1
        assert index.count('class="hf6514-testimonial-zoom"') == 4
        assert index.count('class="hf6514-testimonial-full"') == 1
        assert "Texto redundante de QA" not in index
        assert "Depoimento enviado pela AlphaFest" not in index
        assert index.count("data:image/svg+xml;base64,") == 4
        assert "hf6514-testimonial-dialog" in index
        assert 'name="robots" content="index,follow' in index
        assert zf.read("robots.txt").decode().startswith("User-agent: *")
        assert zf.read("_headers").decode().find("X-Content-Type-Options") >= 0
        assert zf.read("404.html") == index_bytes
        for elemento in ("CLOUDFLARE_API_TOKEN", "SUPABASE_SERVICE_ROLE_KEY"):
            assert elemento not in index, "Encontrada referência a segredo."
        arquivos = len(nomes)

    # Exercita também o extrator que alimenta o deploy, sem chamar o deploy.
    assets, especiais = extrair_pacote_publico(pacote)
    assert assets["/index.html"] == index_bytes
    assert assets["/404.html"] == index_bytes
    assert especiais.get("_headers")
    assert "/STATUS-PRODUCAO.json" not in assets
    assert "/README-PRODUCAO.txt" not in assets
    assert "/manifest.webmanifest" in assets
    assert "/sw.js" in assets

    # Blindagem anti-staging: o ZIP de produção jamais aceita uma faixa
    # explícita de homologação ou uma página marcada para noindex.
    for marcador in ("HOMOLOGAÇÃO", "SITE PARALELO HF40", "noindex,nofollow,noarchive"):
        try:
            preparar_html_producao("<html><head></head><body>" + marcador + "</body></html>")
        except ValueError:
            pass
        else:
            raise AssertionError("O filtro de staging não bloqueou: " + marcador)

    return {
        "resultado": "APROVADO",
        "tipo": "ZIP real montado e auditado somente em memoria",
        "publicado": False,
        "credenciais": False,
        "imagens": 4,
        "arquivo_de_producao_disponibilizado": False,
        "arquivos_no_zip": arquivos,
        "assets_extraidos_cloudflare": len(assets),
        "modulos_especiais": sorted(especiais),
        "hash_sha256_zip_em_memoria": hashlib.sha256(pacote).hexdigest(),
        "fingerprint_assets": fingerprint_pacote(pacote),
        "avisos": [
            "Nenhum arquivo ZIP de produção foi armazenado em artefatos.",
            "Imagens fictícias; falta conferir os depoimentos reais antes da publicação.",
        ],
    }


def main() -> None:
    report = avaliar_pacote()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "RELATORIO_ZIP_HF59.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
