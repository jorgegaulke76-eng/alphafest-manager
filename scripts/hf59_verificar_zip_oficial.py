"""Valida OFFLINE o ZIP OFICIAL do site AlphaFest HF59, sem publicar.
Executar com o ZIP exportado pela Central do Site do Manager atualizado.
Nunca chama Supabase, GitHub ou Cloudflare; nao escreve arquivos.
"""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
from urllib.parse import unquote
import zipfile

OBRIGATORIOS = {
    "index.html", "404.html", "robots.txt", "sitemap.xml",
    "manifest.webmanifest", "sw.js", "_headers", "STATUS-PRODUCAO.json",
}
BLOQUEADOS = (
    "HF59-REVIEW-FICTICIO", "HF59-AUDITORIA-LOCAL",
    "SOMENTE TESTE", "SITE_FICTICIO_PARA_REVISAO",
    "noindex,nofollow,noarchive", "SITE PARALELO HF40",
    "__HF52_PREVIEW_EVENTS", "hf52-pages-protections",
)


class GaleriaHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.nivel = 0
        self.imagens = []
        self.abertos = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set(attrs.get("class", "").split())
        if tag == "button" and "hf6514-testimonial-zoom" in classes:
            self.abertos += 1
            self.nivel += 1
        elif self.nivel and tag == "button":
            self.nivel += 1
        if tag == "img" and self.nivel:
            self.imagens.append(attrs.get("src", ""))

    def handle_endtag(self, tag):
        if tag == "button" and self.nivel:
            self.nivel -= 1


def auditar(pacote: bytes, jpeg_paths: list[str] | None = None) -> dict:
    if len(pacote) > 200 * 1024 * 1024:
        raise ValueError("ZIP maior que o limite preventivo de 200 MB")
    with zipfile.ZipFile(io.BytesIO(pacote)) as z:
        nomes = set(z.namelist())
        faltando = OBRIGATORIOS - nomes
        if faltando:
            raise ValueError("Arquivos obrigatorios ausentes: " + ", ".join(sorted(faltando)))
        if z.testzip() is not None:
            raise ValueError("ZIP danificado")
        index_bytes = z.read("index.html")
        page = index_bytes.decode("utf-8")
        status = json.loads(z.read("STATUS-PRODUCAO.json"))
        if z.read("404.html") != index_bytes:
            raise ValueError("404.html diferente do index.html")
        if status.get("dominio_final") != "alphafest.com.br":
            raise ValueError("Dominio de destino diferente do oficial")
        if not isinstance(status.get("produtos_snapshot"), int) or status["produtos_snapshot"] <= 0:
            raise ValueError("Catalogo vazio no pacote: nao e o snapshot completo")
        versao = str(status.get("versao_manager") or "")
        if not versao:
            raise ValueError("Versao do Manager nao identificada")
        if any(valor.lower() in (page + " " + versao).lower() for valor in BLOQUEADOS):
            raise ValueError("ZIP de previa/teste nao pode ser publicado")
        if page.count("O carinho dos nossos clientes") != 1:
            raise ValueError("Titulo dos depoimentos deve aparecer uma vez")
        if page.count("Cada mensagem que recebemos") != 1:
            raise ValueError("Agradecimento duplicado ou ausente")
        if page.count('class="hf6514-testimonial-full"') != 1:
            raise ValueError("Modal de zoom ausente ou duplicado")
        if "hf50-mobile-more" not in page or "hf6514-testimonial-dialog" not in page:
            raise ValueError("Codigo da HF59 ou da correcao mobile ausente")
        if "X-Content-Type-Options" not in z.read("_headers").decode("utf-8"):
            raise ValueError("Cabecalhos de seguranca ausentes")
        if not z.read("robots.txt").startswith(b"User-agent: *"):
            raise ValueError("robots.txt inesperado")
        if "index,follow" not in page:
            raise ValueError("Indexacao publica nao verificada")
        galeria = GaleriaHTML()
        galeria.feed(page)
        imagens = galeria.imagens
        if len(imagens) != 4 or galeria.abertos != 4:
            raise ValueError(f"Galeria contem {len(imagens)} imagens; esperadas 4")
        if not all(src.startswith(("https://", "data:image/")) for src in imagens):
            raise ValueError("Origem de imagem inesperada")
        if jpeg_paths:
            if len(jpeg_paths) != 4:
                raise ValueError("Passe os quatro JPEGs originais")
            urls = [unquote(src) for src in imagens]
            for item in jpeg_paths:
                nome = Path(item).name
                if not any(nome in src for src in urls):
                    raise ValueError("Um JPEG original nao foi encontrado no HTML")
        resultado = {
            "resultado": "APROVADO PARA REVISAO HUMANA; NAO PUBLICADO",
            "versao_manager": versao,
            "produtos_snapshot": status["produtos_snapshot"],
            "depoimentos_imagem": len(imagens),
            "arquivos_zip": len(nomes),
            "bytes_zip": len(pacote),
            "sha256_zip": hashlib.sha256(pacote).hexdigest(),
            "publicacao": False,
        }
        return resultado


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_oficial", type=Path)
    parser.add_argument("--jpegs", nargs=4, default=None,
                        metavar=("IMG1", "IMG2", "IMG3", "IMG4"))
    args = parser.parse_args()
    try:
        relatorio = auditar(args.zip_oficial.read_bytes(), args.jpegs)
    except (OSError, ValueError, UnicodeError, KeyError, zipfile.BadZipFile) as exc:
        parser.exit(2, "HF59 BLOQUEADO: " + str(exc) + "\n")
    print(json.dumps(relatorio, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
