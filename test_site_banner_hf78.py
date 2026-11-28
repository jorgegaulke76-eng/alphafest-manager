"""HF78 - testes sintéticos, sem fotos de clientes ou publicação."""
from __future__ import annotations

import io
import json
import unittest
import zipfile
from PIL import Image

from site_banner_hf78 import otimizar_banner_inicial_hf78
from site_production_service import gerar_pacote_producao


def png_teste() -> bytes:
    # PNG propositalmente volumoso: pixels e transparência devem ficar idênticos.
    imagem = Image.new("RGBA", (480, 320))
    pixels = imagem.load()
    for y in range(320):
        for x in range(480):
            pixels[x, y] = ((x // 20 * 15) % 256, (y // 20 * 13) % 256, 170, (x // 40 * 25) % 256)
    buf = io.BytesIO()
    imagem.save(buf, format="PNG", compress_level=0)
    return buf.getvalue()


def pagina(caminho: str) -> str:
    return (
        '<!doctype html><html><head><title>AlphaFest</title></head><body>'
        '<section class="hf6514-banner" id="novidades"><div class="hf6514-banner-shell">'
        '<img src="/' + caminho + '" alt="Campanha teste" loading="eager">'
        '</div></section><a href="#produtos">Produtos</a></body></html>'
    )


class BannerHF78(unittest.TestCase):
    def test_variante_lossless_preserva_pixels_original_e_textos(self):
        original = png_teste()
        caminho = "assets/img/" + "1" * 24 + ".png"
        pagina_original = pagina(caminho)
        novo, arquivos, rel = otimizar_banner_inicial_hf78(pagina_original, {caminho: original})
        self.assertTrue(rel["banner_identificado"])
        self.assertTrue(rel["variante_lossless"])
        self.assertGreater(rel["economia_bytes"], 0)
        self.assertEqual(arquivos[caminho], original)
        self.assertIn('fetchpriority="high"', novo)
        self.assertIn('width="480"', novo)
        self.assertIn('height="320"', novo)
        self.assertIn('alt="Campanha teste"', novo)
        self.assertIn('href="#produtos"', novo)
        variante = next((v for k, v in arquivos.items() if k.endswith(".webp")), None)
        self.assertIsNotNone(variante)
        with Image.open(io.BytesIO(original)) as a, Image.open(io.BytesIO(variante)) as b:
            self.assertEqual(a.size, b.size)
            self.assertEqual(a.convert("RGBA").tobytes(), b.convert("RGBA").tobytes())

    def test_sem_banner_ou_png_nao_modifica(self):
        pagina_html = '<html><img src="https://exemplo.invalid/banner.png"></html>'
        novo, arquivos, rel = otimizar_banner_inicial_hf78(pagina_html, {})
        self.assertEqual(novo, pagina_html)
        self.assertEqual(arquivos, {})
        self.assertFalse(rel["banner_identificado"])

    def test_pacote_com_banner_preserva_originais_e_diagnostico_privado(self):
        import base64
        png = png_teste()
        uri = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
        html = pagina(uri).replace('src="/data:image/', 'src="data:image/')
        # A função de produção primeiro extrai a imagem inline e depois a otimiza.
        pacote = gerar_pacote_producao(html)
        with zipfile.ZipFile(io.BytesIO(pacote)) as zf:
            status = json.loads(zf.read("STATUS-PRODUCAO.json"))
            self.assertIn("hf78_banner_inicial", status)
            self.assertTrue(status["hf78_banner_inicial"]["variante_lossless"])
            assets = [n for n in zf.namelist() if n.startswith("assets/img/")]
            self.assertTrue(any(n.endswith(".png") and zf.read(n) == png for n in assets))
            self.assertTrue(any(n.endswith(".webp") for n in assets))
            home = zf.read("index.html").decode("utf-8")
            self.assertIn('fetchpriority="high"', home)
            self.assertNotIn(uri, home)

    def test_imagem_pequena_ou_corrompida_nao_produz_alteracao(self):
        caminho = "assets/img/" + "c"*24 + ".png"
        pagina_html = pagina(caminho)
        novo, arquivos, rel = otimizar_banner_inicial_hf78(pagina_html, {caminho: b"nao-e-png"})
        self.assertFalse(rel["variante_lossless"])
        self.assertEqual(arquivos[caminho], b"nao-e-png")
        self.assertIn('/' + caminho, novo)


if __name__ == "__main__":
    unittest.main()
