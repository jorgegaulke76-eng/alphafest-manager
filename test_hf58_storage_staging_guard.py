"""Ensaios offline das barreiras para validar Storage em Supabase separado.

NENHUM teste usa URL real nem segredo. Simula HTTP em memória.
"""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch
import sys
from types import SimpleNamespace
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))

import validar_storage_hf58_staging as stage


STAGE_REF = "abcdefghijklmnopqrst"
PROD_REF = "zyxwvutsrqponmlkjihg"
STAGE = f"https://{STAGE_REF}.supabase.co"
PROD = f"https://{PROD_REF}.supabase.co"
KEY = "sb_secret_chave_ficticia_que_nunca_funciona"
OK = stage.CONFIRMACAO


def destino():
    return stage.validar_destinos(STAGE, PROD, STAGE_REF, OK)


class RespostaFicticia:
    def __init__(self, status_code, content=b"", payload=None):
        self.status_code = status_code
        self.content = content
        self.payload = payload
    def json(self):
        return self.payload


class SessaoFicticia:
    def __init__(self, *, nao_temos_marcador=False, bucket_publico=True, erro_de_upload=False):
        self.mais = {}
        self.deletados = []
        self.uploads = []
        self.nao_temos_marcador = nao_temos_marcador
        self.bucket_publico = bucket_publico
        self.erro_de_upload = erro_de_upload
    def get(self, url, **kwargs):
        if url == STAGE + "/storage/v1/bucket/catalogo":
            return RespostaFicticia(200, payload={"id": "catalogo", "public": self.bucket_publico})
        if url.endswith(destino().sentinela):
            return (RespostaFicticia(404) if self.nao_temos_marcador else
                    RespostaFicticia(200, content=f"ALPHAFEST_HF58_STAGING_ONLY:{STAGE_REF}\n".encode()))
        prefixo = STAGE + "/storage/v1/object/public/catalogo/"
        if url.startswith(prefixo) and url in self.mais:
            return RespostaFicticia(200, content=self.mais[url])
        return RespostaFicticia(404)
    def post(self, url, **kwargs):
        self.uploads.append(url)
        if self.erro_de_upload:
            return self._erro403(url)
        prefixo = STAGE + "/storage/v1/object/catalogo/"
        if not url.startswith(prefixo):
            raise AssertionError("Tentativa de gravar fora do bucket catalogo fictício")
        publico = url.replace("/object/catalogo/", "/object/public/catalogo/", 1)
        self.mais[publico] = kwargs["data"]
        return self._sucesso(url)
    def delete(self, url, **kwargs):
        prefixo = STAGE + "/storage/v1/object/catalogo/"
        if not url.startswith(prefixo):
            raise AssertionError("Tentativa de exclusão fora do bucket catalogo fictício")
        publico = url.replace("/object/catalogo/", "/object/public/catalogo/", 1)
        self.mais.pop(publico, None)
        self.deletados.append(url)
        return RespostaFicticia(200)
    @staticmethod
    def _sucesso(url):
        import requests
        r = requests.Response()
        r.status_code = 201
        r.url = url
        return r
    @staticmethod
    def _erro403(url):
        import requests
        r = requests.Response()
        r.status_code = 403
        r.url = url
        return r


class ProtecaoHomologacaoHF58Tests(unittest.TestCase):
    def test_producao_igual_staging_bloqueia(self):
        with self.assertRaisesRegex(stage.BloqueioHomologacao, "mesmo projeto"):
            stage.validar_destinos(STAGE, STAGE, STAGE_REF, OK)

    def test_ref_digitada_ou_confirmacao_incorreta_bloqueia(self):
        with self.assertRaises(stage.BloqueioHomologacao):
            stage.validar_destinos(STAGE, PROD, PROD_REF, OK)
        with self.assertRaises(stage.BloqueioHomologacao):
            stage.validar_destinos(STAGE, PROD, STAGE_REF, "SIM")

    def test_url_personalizada_http_ou_caminho_bloqueados(self):
        for url in ("http://"+STAGE_REF+".supabase.co", "https://example.com",
                    STAGE+"/rest/v1", "https://localhost:54321", STAGE+"/?token=123"):
            with self.subTest(url=url), self.assertRaises(stage.BloqueioHomologacao):
                stage.validar_destinos(url, PROD, STAGE_REF, OK)

    def test_sem_sentinela_nao_envia(self):
        sessao = SessaoFicticia(nao_temos_marcador=True)
        with self.assertRaisesRegex(stage.BloqueioHomologacao, "sentinela"):
            stage.exercitar_upload(destino(), KEY, sessao)
        self.assertEqual(sessao.uploads, [])

    def test_bucket_nao_publico_nao_envia(self):
        sessao = SessaoFicticia(bucket_publico=False)
        with self.assertRaisesRegex(stage.BloqueioHomologacao, "público"):
            stage.exercitar_upload(destino(), KEY, sessao)
        self.assertEqual(sessao.uploads, [])

    def test_upload_download_hash_e_exclusao_sem_supabase_real(self):
        sessao = SessaoFicticia()
        msg = stage.exercitar_upload(destino(), KEY, sessao)
        self.assertTrue(msg.startswith("APROVADO:"))
        self.assertEqual(len(sessao.uploads), 1)
        self.assertEqual(len(sessao.deletados), 1)
        self.assertIn("biblioteca/HF58_STAGING_ONLY/", sessao.uploads[0])
        self.assertEqual(sessao.mais, {})

    def test_erro_upload_403_nao_persiste_local_nem_declara_sucesso(self):
        sessao = SessaoFicticia(erro_de_upload=True)
        with self.assertRaisesRegex(stage.BloqueioHomologacao, "não foi confirmado"):
            stage.exercitar_upload(destino(), KEY, sessao)
        self.assertEqual(len(sessao.uploads), 1)
        self.assertEqual(sessao.deletados, [])

    def test_sem_executar_nao_le_chave_e_nao_envia(self):
        with patch.object(stage.getpass, "getpass", side_effect=AssertionError("chave não pode ser lida")):
            self.assertEqual(stage.main([]), 0)


if __name__ == "__main__":
    unittest.main()
