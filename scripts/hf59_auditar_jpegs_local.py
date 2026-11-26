"""Auditoria HF59 exclusivamente local: quatro JPEGs, ZIP somente em memoria.

Nao envia dados a Supabase, GitHub ou Cloudflare e nao grava HTML/ZIP.
Usar em copia local da branch HF59, nunca na CI com JPEGs reais.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def auditar(imagens: list[bytes]) -> dict:
    from PIL import Image
    from site_completo_service import gerar_html_site_completo
    from site_production_service import gerar_pacote_producao
    from site_cloudflare_publish_service import extrair_pacote_publico

    if len(imagens) != 4:
        raise ValueError("Informe exatamente quatro JPEGs.")
    registros, info = [], []
    for i, dados in enumerate(imagens, 1):
        if not dados or len(dados) > 8 * 1024 * 1024:
            raise ValueError(f"Imagem {i}: tamanho invalido.")
        with Image.open(io.BytesIO(dados)) as img:
            img.load()
            if img.format != "JPEG":
                raise ValueError(f"Imagem {i}: formato nao e JPEG.")
            largura, altura = img.size
        info.append({"imagem": i, "bytes": len(dados), "largura": largura, "altura": altura})
        registros.append({
            "kind": "image", "active": True, "id": f"local-{i}",
            "name": f"Depoimento {i}",
            "image_src": "data:image/jpeg;base64," + base64.b64encode(dados).decode("ascii"),
            "text": "TEXTO REDUNDANTE NAO EXIBIR",
        })
    site = gerar_html_site_completo(
        [], {"nome": "AlphaFest - TESTE LOCAL, NAO PUBLICAR"},
        home_content_config={"testimonials": registros},
        modo_preview=True, visual_hf48=True,
    )
    if site.count('class="hf6514-testimonial-zoom"') != 4:
        raise AssertionError("Contagem de imagens no HTML incorreta.")
    if "TEXTO REDUNDANTE NAO EXIBIR" in site:
        raise AssertionError("Legenda duplicada encontrada.")
    pacote = gerar_pacote_producao(
        site, total_produtos=0, versao_manager="HF59-AUDITORIA-LOCAL",
        adsense_publisher_id="", dicas_content=[], posts_content=[],
    )
    with zipfile.ZipFile(io.BytesIO(pacote)) as z:
        if z.testzip() is not None:
            raise AssertionError("ZIP corrompido.")
        index = z.read("index.html").decode("utf-8")
        for dados in imagens:
            uri = "data:image/jpeg;base64," + base64.b64encode(dados).decode("ascii")
            if index.count(uri) != 1:
                raise AssertionError("Imagem ausente ou duplicada no ZIP.")
        for nome in ("404.html", "manifest.webmanifest", "sw.js", "robots.txt", "_headers"):
            z.getinfo(nome)
        arquivos = len(z.namelist())
    assets, especiais = extrair_pacote_publico(pacote)
    if "/index.html" not in assets or not especiais.get("_headers"):
        raise AssertionError("Extracao Cloudflare incompleta.")
    return {
        "resultado": "APROVADO", "imagens": info, "arquivos_zip": arquivos,
        "assets": len(assets), "publicado": False,
        "limite": "Nao valida textos ou ordem reais do Manager nem substitui revisao visual."
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("imagens", nargs="*", help="Quatro caminhos locais de JPEGs")
    parser.add_argument("--self-test", action="store_true", help="Gera quatro JPEGs ficticios em memoria")
    args = parser.parse_args()
    if args.self_test:
        if args.imagens:
            parser.error("Nao misture --self-test e arquivos reais.")
        from PIL import Image
        entradas = []
        for w, h in ((440, 680), (640, 350), (430, 540), (520, 760)):
            with io.BytesIO() as buf:
                with Image.new("RGB", (w, h), (220, 239, 251)) as image:
                    image.save(buf, format="JPEG", quality=85)
                entradas.append(buf.getvalue())
    else:
        if len(args.imagens) != 4:
            parser.error("Informe quatro JPEGs locais ou --self-test.")
        entradas = [Path(p).read_bytes() for p in args.imagens]
    try:
        resultado = auditar(entradas)
    except (AssertionError, ValueError, OSError, KeyError, zipfile.BadZipFile) as exc:
        print("HF59 NAO APROVADO: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
