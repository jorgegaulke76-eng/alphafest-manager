"""HF76: imagens de HTML como assets, sem alterar os bytes ou os registros."""
import base64
import io
import re
import unittest
import zipfile

from site_imagens_hf76 import extrair_imagens_inline_hf76
from site_cloudflare_publish_service import extrair_pacote_publico
from site_production_service import gerar_pacote_producao


PNG = b"\\x89PNG\\r\\n\\x1a\\n" + b"imagem-ficticia-de-teste"
DATA = "data:image/png;base64," + base64.b64encode(PNG).decode("ascii")


class ImagensHF76(unittest.TestCase):
    def test_reuso_igual_e_ordem_de_imagens(self):
        html = ('<img loading="lazy" src="' + DATA + '" alt="1">'
                '<img src="' + DATA + '" alt="2">')
        novo, arquivos = extrair_imagens_inline_hf76(html)
        self.assertEqual(len(arquivos), 1)
        self.assertNotIn("data:image/png;base64,", novo)
        caminho = next(iter(arquivos))
        self.assertEqual(novo.count("/" + caminho), 2)
        self.assertEqual(arquivos[caminho], PNG)

    def test_nao_reescreve_json_script_ou_uri_invalida(self):
        html = ('<script>const original="' + DATA + '"</script>'
                '<img src="data:image/png;base64,@@@">'
                '<img src="https://exemplo.invalid/foto.png">')
        novo, arquivos = extrair_imagens_inline_hf76(html)
        self.assertEqual(novo, html)
        self.assertEqual(arquivos, {})

    def test_pacote_publico_expoe_arquivo_estatico(self):
        site = ('<!doctype html><html lang="pt-BR"><head><title>AlphaFest</title>'
                '</head><body><h1>Exemplo</h1><img src="' + DATA + '"></body></html>')
        pacote = gerar_pacote_producao(site)
        with zipfile.ZipFile(io.BytesIO(pacote)) as z:
            nomes = z.namelist()
            imagem = [n for n in nomes if n.startswith("assets/img/")]
            self.assertEqual(len(imagem), 1)
            self.assertEqual(z.read(imagem[0]), PNG)
            home = z.read("index.html").decode("utf-8")
            self.assertIn('/' + imagem[0], home)
            self.assertNotIn(DATA, home)
            self.assertIn(b"max-age=31536000", z.read("_headers"))
        assets, _ = extrair_pacote_publico(pacote)
        self.assertIn("/" + imagem[0], assets)
        self.assertEqual(assets["/" + imagem[0]], PNG)

    def test_nao_aceitar_ficheiro_falso_na_publicacao(self):
        pacote = io.BytesIO()
        with zipfile.ZipFile(pacote, "w") as z:
            z.writestr("index.html", "<p>HTML</p>")
            z.writestr("privacidade/index.html", "<p>Privacidade</p>")
            z.writestr("como-encomendar/index.html", "<p>Como encomendar</p>")
            z.writestr("assets/img/nao-validado.png", PNG)
            z.writestr("assets/img/" + "a"*24 + ".exe", b"executavel")
        assets, _ = extrair_pacote_publico(pacote.getvalue())
        self.assertNotIn("/assets/img/nao-validado.png", assets)
        self.assertEqual(len([k for k in assets if k.startswith("/assets/img")]), 0)


if __name__ == "__main__":
    unittest.main()
