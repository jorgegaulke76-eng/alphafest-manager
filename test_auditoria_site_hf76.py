"""HF76: auditoria privada da reducao do HTML, sem acesso a clientes."""
from __future__ import annotations
import base64
import io
import json
import unittest
import zipfile
from site_production_service import gerar_pacote_producao
from site_cloudflare_publish_service import extrair_pacote_publico

IMAGEM = b"imagem-de-teste-nao-real"
DATA = "data:image/png;base64," + base64.b64encode(IMAGEM).decode("ascii")


class TestAuditoriaPacoteHF76(unittest.TestCase):
    def test_snapshot_indica_bytes_e_arquivos_sem_expor_dados(self):
        pagina = (
            '<!doctype html><html lang="pt-BR"><head><title>AlphaFest</title></head><body>'
            '<article class="product-card" data-detail-image="' + DATA + '">'
            '<img src="' + DATA + '" alt="Produto teste"></article></body></html>'
        )
        pacote = gerar_pacote_producao(pagina)
        with zipfile.ZipFile(io.BytesIO(pacote)) as zf:
            status = json.loads(zf.read("STATUS-PRODUCAO.json").decode("utf-8"))
            imagem = status["hf76_imagens_home"]
            self.assertGreater(imagem["html_antes_bytes"], imagem["html_depois_bytes"])
            self.assertEqual(
                imagem["html_reducao_bytes"],
                imagem["html_antes_bytes"] - imagem["html_depois_bytes"],
            )
            self.assertGreaterEqual(imagem["arquivos_separados"], 1)
            self.assertGreaterEqual(imagem["total_bytes_imagens_originais"], len(IMAGEM))
            self.assertNotIn("data:image", json.dumps(imagem))
            self.assertIn("hf76_imagens_paginas_adicionais", status)
            html = zf.read("index.html").decode("utf-8")
            self.assertNotIn(DATA, html)
            self.assertIn("data-detail-image=\"/assets/img/", html)
            self.assertIn("src=\"/assets/img/", html)
        assets, _ = extrair_pacote_publico(pacote)
        self.assertTrue(any(k.startswith("/assets/img/") and v == IMAGEM for k, v in assets.items()))
        self.assertNotIn("/STATUS-PRODUCAO.json", assets)

    def test_sem_imagens_extras_reporta_contagem_nao_negativa(self):
        pacote = gerar_pacote_producao('<html><head></head><body><p>Teste</p></body></html>')
        with zipfile.ZipFile(io.BytesIO(pacote)) as zf:
            status = json.loads(zf.read("STATUS-PRODUCAO.json"))
        self.assertGreaterEqual(status["hf76_imagens_home"]["html_reducao_bytes"], 0)
        self.assertGreaterEqual(status["hf76_imagens_paginas_adicionais"]["arquivos_distintos"], 0)


if __name__ == "__main__":
    unittest.main()
