"""Testes de bytes persistidos com disco/servidor HTTP local, sem Supabase real."""
from __future__ import annotations

import tempfile
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import requests
import cloud_db


def arquivo(nome, dados):
    return SimpleNamespace(name=nome, type="image/png", getbuffer=lambda: memoryview(dados))


@contextmanager
def servidor_ficticio():
    objetos, chaves = {}, []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            prefix = "/storage/v1/object/catalogo/"
            if not self.path.startswith(prefix):
                return self.send_error(404)
            objetos[self.path[len(prefix):]] = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            chaves.append(self.headers.get("apikey"))
            self.send_response(201)
            self.end_headers()
            self.wfile.write(b'{"Key":"gravado"}')
        def do_GET(self):
            prefix = "/storage/v1/object/public/catalogo/"
            if not self.path.startswith(prefix) or self.path[len(prefix):] not in objetos:
                return self.send_error(404)
            dados = objetos[self.path[len(prefix):]]
            self.send_response(200)
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)
        def log_message(self, *args):
            return
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=srv.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{srv.server_port}", objetos, chaves
    finally:
        srv.shutdown()
        srv.server_close()
        worker.join(timeout=3)


class StorageIsoladoHF58Tests(unittest.TestCase):
    def test_offline_preserva_bytes_em_pasta_temporaria(self):
        dados = b'PNG FICTICIO \x00\x01\xff'
        with tempfile.TemporaryDirectory(prefix="hf58-offline-") as pasta:
            with patch.object(cloud_db, "online_configured", return_value=False), \
                 patch.object(cloud_db._SESSION, "post", side_effect=AssertionError("HTTP proibido")):
                caminho = cloud_db.upload_library_file(arquivo("arte_ficticia.png", dados), produto_nome="HF58", local_upload_dir=pasta)
            self.assertTrue(caminho)
            self.assertEqual(Path(caminho).read_bytes(), dados)
            self.assertTrue(Path(caminho).is_relative_to(Path(pasta)))

    def test_http_local_recebe_e_devolve_bytes(self):
        dados = b'ARTE FICTICIA v2 \x00\x88\x99'
        with tempfile.TemporaryDirectory(prefix="hf58-http-") as pasta:
            with servidor_ficticio() as (url, objetos, chaves):
                with patch.object(cloud_db, "_config", return_value=(url, "chave_teste")):
                    caminho = cloud_db.upload_library_file(arquivo("Arte v2.png", dados), produto_nome="PROJETO_FICTICIO", local_upload_dir=pasta)
                self.assertTrue(caminho.startswith(url + "/storage/v1/object/public/catalogo/"))
                self.assertEqual(requests.get(caminho, timeout=5).content, dados)
                self.assertEqual(len(objetos), 1)
                self.assertEqual(chaves, ["chave_teste"])
                self.assertEqual(list(Path(pasta).rglob("*")), [])

    def test_timeout_online_nao_finge_salvamento_local(self):
        with tempfile.TemporaryDirectory(prefix="hf58-timeout-") as pasta:
            with patch.object(cloud_db, "_config", return_value=("http://127.0.0.1:1", "chave_teste")), \
                 patch.object(cloud_db._SESSION, "post", side_effect=requests.Timeout("erro simulado")):
                caminho = cloud_db.upload_library_file(arquivo("arte_v2.png", b'FICTICIO'), produto_nome="HF58", local_upload_dir=pasta)
            self.assertEqual(caminho, "")
            self.assertEqual(list(Path(pasta).rglob("*")), [])

    def test_http_403_online_nao_finge_salvamento_local(self):
        response = requests.Response()
        response.status_code = 403
        response.url = "http://127.0.0.1:1/storage/v1/object/catalogo/arte"
        with tempfile.TemporaryDirectory(prefix="hf58-http403-") as pasta:
            with patch.object(cloud_db, "_config", return_value=("http://127.0.0.1:1", "chave_teste")), \
                 patch.object(cloud_db._SESSION, "post", return_value=response):
                caminho = cloud_db.upload_library_file(arquivo("arte_v2.png", b'FICTICIO'), produto_nome="HF58", local_upload_dir=pasta)
            self.assertEqual(caminho, "")
            self.assertEqual(list(Path(pasta).rglob("*")), [])


if __name__ == "__main__":
    unittest.main()
