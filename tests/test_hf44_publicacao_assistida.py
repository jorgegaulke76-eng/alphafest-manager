import io
import json
import zipfile
import unittest
from pathlib import Path

from site_cloudflare_publish_service import (
    CloudflarePublishError,
    criar_manifesto,
    extrair_pacote_publico,
    fingerprint_pacote,
    publicar_pacote,
)
from site_production_service import gerar_pacote_producao, resumo_producao


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
        self.ok = 200 <= status < 300

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, manifest_hashes):
        self.calls = []
        self.manifest_hashes = list(manifest_hashes)

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        if url.endswith("/assets-upload-session"):
            return FakeResponse({
                "success": True,
                "result": {"jwt": "upload-jwt", "buckets": [self.manifest_hashes]},
                "errors": [],
            })
        if "/workers/assets/upload?base64=true" in url:
            return FakeResponse({"success": True, "result": {"jwt": "completion-jwt"}, "errors": []}, 201)
        if "/workers/workers/alphafest-novo/versions?deploy=true" in url:
            return FakeResponse({
                "success": True,
                "result": {"id": "182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e", "number": 44},
                "errors": [],
            })
        raise AssertionError(url)


class HF44PublicacaoAssistidaTests(unittest.TestCase):
    def pacote(self):
        return gerar_pacote_producao(
            "<html><head></head><body>HF44 vitrine</body></html>",
            total_produtos=17,
            versao_manager="20.4.9-I8.13.5-HF44",
        )

    def test_pacote_publico_exclui_readme_status_e_trata_headers_como_modulo(self):
        assets, modulos = extrair_pacote_publico(self.pacote())
        self.assertEqual(set(assets), {"/index.html", "/404.html", "/robots.txt", "/sitemap.xml"})
        self.assertIn("_headers", modulos)
        self.assertNotIn("/README-PRODUCAO.txt", assets)
        self.assertNotIn("/STATUS-PRODUCAO.json", assets)

    def test_fingerprint_independe_do_timestamp_do_status(self):
        a = self.pacote()
        b = self.pacote()
        self.assertEqual(fingerprint_pacote(a), fingerprint_pacote(b))

    def test_manifesto_tem_hash_32_hex_e_tamanho_real(self):
        assets, _ = extrair_pacote_publico(self.pacote())
        manifesto, mapa = criar_manifesto(assets)
        self.assertEqual(len(manifesto), 4)
        for path, meta in manifesto.items():
            self.assertEqual(len(meta["hash"]), 32)
            int(meta["hash"], 16)
            self.assertEqual(meta["size"], len(assets[path]))
            self.assertIn(mapa[meta["hash"]], assets)

    def test_publicacao_faz_manifest_upload_e_deploy_sem_dns(self):
        pacote = self.pacote()
        assets, _ = extrair_pacote_publico(pacote)
        manifesto, _ = criar_manifesto(assets)
        fake = FakeSession(sorted({meta["hash"] for meta in manifesto.values()}))
        result = publicar_pacote(
            pacote,
            account_id="0123456789abcdef0123456789abcdef",
            api_token="token-seguro-de-teste-1234567890",
            worker_name="alphafest-novo",
            session=fake,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["assets_total"], 4)
        self.assertGreaterEqual(result["assets_enviados"], 3)
        self.assertEqual(result["version_number"], 44)
        urls = [c[1] for c in fake.calls]
        self.assertTrue(any("assets-upload-session" in u for u in urls))
        self.assertTrue(any("workers/assets/upload?base64=true" in u for u in urls))
        self.assertTrue(any("versions?deploy=true" in u for u in urls))
        self.assertFalse(any("/dns_records" in u or "/zones/" in u for u in urls))
        version_call = next(c for c in fake.calls if "versions?deploy=true" in c[1])
        body = version_call[2]["json"]
        self.assertEqual(body["bindings"], [{"type": "assets", "name": "ASSETS"}])
        self.assertEqual(body["assets"]["config"]["not_found_handling"], "404-page")
        nomes_modulos = {m["name"] for m in body["modules"]}
        self.assertIn("main.js", nomes_modulos)
        self.assertIn("_headers", nomes_modulos)

    def test_erro_cloudflare_interrompe_sem_tentar_deploy(self):
        class Falha:
            def post(self, url, **kwargs):
                return FakeResponse({"success": False, "errors": [{"code": 10000, "message": "Authentication error"}]}, 403)
        with self.assertRaises(CloudflarePublishError):
            publicar_pacote(
                self.pacote(),
                account_id="0123456789abcdef0123456789abcdef",
                api_token="token-seguro-de-teste-1234567890",
                session=Falha(),
            )

    def test_status_hf44_reflete_www_301(self):
        self.assertEqual(resumo_producao(total_produtos=17)["www"], "301 → alphafest.com.br")

    def test_ui_expoe_publicacao_assistida_e_fallback(self):
        app = Path("app.py").read_text(encoding="utf-8")
        self.assertIn("HF44 · Publicação assistida", app)
        self.assertIn('"🚀 Produção oficial — HF44"', app)
        self.assertIn('"🚀 Publicar site agora"', app)
        self.assertIn('"🔎 Testar conexão sem publicar"', app)
        self.assertIn("alphafest-site-producao-hf44.zip", app)
        self.assertIn('versao_manager="20.4.9-I8.13.5-HF44"', app)
        self.assertIn("não é gravado em JSON", app)


if __name__ == "__main__":
    unittest.main()
