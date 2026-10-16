"""Testes de concorrência do salvamento real do catálogo com HTTP simulado.

Não acessa rede, credenciais, app.py em execução ou o banco de produção.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import cloud_db
from catalogo_modalidade_preco_service import aplicar_modalidade


class TestConcorrenciaCatalogoIsolado(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="alphafest_cas_")
        self.addCleanup(self.temp.cleanup)
        self.path = str(Path(self.temp.name) / "catalogo.json")
        self.anterior = [{"Nome": "Caneca ficticia", "Preco": "38,00",
                          "ExibirPrecoSite": False, "Estoque": 5}]
        self.novo = json.loads(json.dumps(self.anterior))
        aplicar_modalidade(self.novo[0], "fixo")
        Path(self.path).write_text(json.dumps(self.anterior), encoding="utf-8")

    def ambiente(self):
        from contextlib import ExitStack
        stack = ExitStack()
        stack.enter_context(patch.object(cloud_db, "online_configured", return_value=True))
        stack.enter_context(patch.object(cloud_db, "_config", return_value=("https://example.invalid", "fake")))
        stack.enter_context(patch.object(cloud_db, "_headers", return_value={}))
        return stack

    def test_rejeita_versao_remota_mais_recente_sem_sobrescrever(self):
        remoto = json.loads(json.dumps(self.anterior))
        remoto[0]["Estoque"] = 9  # alteração concorrente
        leitura = Mock()
        leitura.json.return_value = [{"value": remoto, "updated_at": "v2"}]
        with self.ambiente(), \
             patch.object(cloud_db._SESSION, "get", return_value=leitura), \
             patch.object(cloud_db._SESSION, "patch") as escrita:
            ok, motivo = cloud_db.save_document_cas(
                "catalogo_db", self.anterior, self.novo, self.path)
        self.assertFalse(ok)
        self.assertIn("conflito", motivo)
        escrita.assert_not_called()
        self.assertEqual(json.loads(Path(self.path).read_text()), self.anterior)

    def test_conflito_entre_leitura_e_patch_sem_backup_novo(self):
        leitura = Mock()
        leitura.json.return_value = [{"value": self.anterior, "updated_at": "v1"}]
        escrita = Mock()
        escrita.json.return_value = []  # zero linhas atualizadas, outro usuário chegou primeiro
        with self.ambiente(), \
             patch.object(cloud_db._SESSION, "get", return_value=leitura), \
             patch.object(cloud_db._SESSION, "patch", return_value=escrita):
            ok, motivo = cloud_db.save_document_cas(
                "catalogo_db", self.anterior, self.novo, self.path, retries=1)
        self.assertFalse(ok)
        self.assertIn("conflito", motivo)
        self.assertEqual(json.loads(Path(self.path).read_text()), self.anterior)

    def test_confirmacao_cas_salva_e_preserva_valor(self):
        leitura = Mock()
        leitura.json.return_value = [{"value": self.anterior, "updated_at": "v1"}]
        escrita = Mock()
        escrita.json.return_value = [{"key": "catalogo_db"}]
        with self.ambiente(), \
             patch.object(cloud_db._SESSION, "get", return_value=leitura), \
             patch.object(cloud_db._SESSION, "patch", return_value=escrita) as patch_http:
            ok, motivo = cloud_db.save_document_cas(
                "catalogo_db", self.anterior, self.novo, self.path)
        self.assertTrue(ok)
        self.assertEqual(motivo, "online")
        self.assertEqual(patch_http.call_args.kwargs["params"]["updated_at"], "eq.v1")
        lido = json.loads(Path(self.path).read_text(encoding="utf-8"))
        self.assertEqual(lido[0]["Preco"], "38,00")
        self.assertEqual(lido[0]["Estoque"], 5)
        self.assertEqual(lido[0]["ModalidadePrecoSite"], "fixo")


if __name__ == "__main__":
    unittest.main()
