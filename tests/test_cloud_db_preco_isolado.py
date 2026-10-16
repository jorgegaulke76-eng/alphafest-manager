"""Homologacao sem rede da camada real cloud_db.save_document/load_document.

Usa mocks do HTTP e um diretório temporário. Nunca usa Secrets, credenciais,
URL de produção, app_data real ou publicação.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch, Mock

import cloud_db
from catalogo_modalidade_preco_service import aplicar_modalidade, modalidade_atual


class TestGravacaoCamadaOficialIsolada(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="alphafest_cloud_mock_")
        self.addCleanup(self.temp.cleanup)
        self.arquivo = str(Path(self.temp.name) / "catalogo_db.json")
        self.base = [{"Nome": "Caneca ficticia", "Preco": "38,00",
                      "ExibirPrecoSite": False, "Estoque": 5}]
        self.alterado = json.loads(json.dumps(self.base))
        aplicar_modalidade(self.alterado[0], "a_partir")

    def test_sem_configuracao_nao_confirma_online(self):
        with patch.object(cloud_db, "online_configured", return_value=False):
            ok = cloud_db.save_document("catalogo_db", self.alterado, self.arquivo)
            reaberto = cloud_db.load_document("catalogo_db", self.arquivo, [])
        self.assertFalse(ok, "Não pode reportar sucesso sem banco online")
        self.assertEqual(modalidade_atual(reaberto[0]), "a_partir")
        self.assertEqual(reaberto[0]["Preco"], "38,00")

    def test_confirmacao_http_e_reabertura(self):
        resposta_post = Mock()
        resposta_post.raise_for_status.return_value = None
        resposta_get = Mock()
        resposta_get.raise_for_status.return_value = None
        resposta_get.json.return_value = [{"value": self.alterado}]
        with patch.object(cloud_db, "online_configured", return_value=True), \
             patch.object(cloud_db, "_config", return_value=("https://example.invalid", "key-ficticia")), \
             patch.object(cloud_db, "_headers", return_value={}), \
             patch.object(cloud_db._SESSION, "post", return_value=resposta_post) as post, \
             patch.object(cloud_db._SESSION, "get", return_value=resposta_get):
            self.assertTrue(cloud_db.save_document("catalogo_db", self.alterado, self.arquivo))
            lido = cloud_db.load_document("catalogo_db", self.arquivo, [])
            self.assertEqual(post.call_count, 1)
        self.assertEqual(modalidade_atual(lido[0]), "a_partir")
        self.assertEqual(lido[0]["Preco"], "38,00")

    def test_falha_http_nao_sobrescreve_backup_local(self):
        import requests
        Path(self.arquivo).write_text(json.dumps(self.base), encoding="utf-8")
        with patch.object(cloud_db, "online_configured", return_value=True), \
             patch.object(cloud_db, "_config", return_value=("https://example.invalid", "key-ficticia")), \
             patch.object(cloud_db, "_headers", return_value={}), \
             patch.object(cloud_db._SESSION, "post", side_effect=requests.ConnectionError("offline")):
            ok = cloud_db.save_document("catalogo_db", self.alterado, self.arquivo)
        self.assertFalse(ok)
        atual = json.loads(Path(self.arquivo).read_text(encoding="utf-8"))
        self.assertNotIn("ModalidadePrecoSite", atual[0])
        self.assertEqual(atual[0]["Preco"], "38,00")


if __name__ == "__main__":
    import unittest
    unittest.main()
