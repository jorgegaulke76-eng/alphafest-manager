import io
import json
import unittest
import zipfile
from pathlib import Path

from site_cutover_service import (
    gerar_checklist_pre_virada,
    gerar_ficha_backup_dns,
    gerar_kit_pre_virada,
    gerar_plano_rollback,
    resumo_pre_virada,
)


class HF41PreViradaTests(unittest.TestCase):
    def test_estado_conservador_nao_autoriza_dns(self):
        r = resumo_pre_virada()
        self.assertEqual(r["staging_externo"], "Homologado")
        self.assertFalse(r["dns_alterado"])
        self.assertEqual(r["backup_dns"], "Pendente")
        self.assertFalse(r["pronto_para_mudar_dns"])

    def test_ficha_protege_email_e_registros(self):
        txt = gerar_ficha_backup_dns()
        for termo in ["A/AAAA", "CNAME", "MX", "TXT", "Nameservers atuais"]:
            self.assertIn(termo, txt)
        self.assertIn("NÃO ALTERAR NADA", txt)

    def test_rollback_nao_cancela_hospedagem_antiga(self):
        txt = gerar_plano_rollback()
        self.assertIn("Não cancelar Wix/hospedagem antiga", txt)
        self.assertIn("Restaurar os registros/NS", txt)

    def test_checklist_marca_homologacao_e_dns_pendente(self):
        txt = gerar_checklist_pre_virada()
        self.assertIn("[x] Staging externo homologado", txt)
        self.assertIn("[ ] Salvar screenshot/backup", txt)
        self.assertIn("Confirmar que e-mail não será afetado", txt)

    def test_kit_nao_contem_cname_nem_comando_dns(self):
        data = gerar_kit_pre_virada()
        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            nomes = set(zf.namelist())
            self.assertEqual(nomes, {
                "BACKUP-DNS-ATUAL.txt",
                "CHECKLIST-PRE-VIRADA-HF41.txt",
                "ROLLBACK-DNS.txt",
                "STATUS-PRE-VIRADA.json",
            })
            self.assertNotIn("CNAME", nomes)
            status = json.loads(zf.read("STATUS-PRE-VIRADA.json").decode("utf-8"))
            self.assertFalse(status["dns_alterado"])
            self.assertFalse(status["pronto_para_mudar_dns"])

    def test_ui_contract(self):
        app = Path("app.py").read_text(encoding="utf-8")
        self.assertIn('"🔐 Preparação da virada do domínio — HF41 (concluída)"', app)
        self.assertIn('"⬇️ Baixar kit de segurança pré-virada (ZIP)"', app)
        self.assertIn('versao_manager="20.4.9-I8.13.5-HF41"', app)


if __name__ == "__main__":
    unittest.main()
