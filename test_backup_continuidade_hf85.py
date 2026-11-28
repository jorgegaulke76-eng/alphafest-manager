"""HF85 — backup diagnostic offline; no database, no personal information."""
import unittest
from datetime import datetime, timedelta, timezone

from backup_continuidade_hf85 import diagnosticar_backups, metadados_backup_registro

UTC = timezone.utc
NOW = datetime(2026, 11, 28, 18, 0, tzinfo=UTC)


def registro(horas_atras=2, **kwargs):
    d = {
        "criado_em": (NOW - timedelta(hours=horas_atras)).isoformat(),
        "sha256": "a" * 64,
        "tipo": "automatico",
        "documentos": {"cliente_teste": {"nome": "NAO_PUBLICAR"}},
    }
    d.update(kwargs)
    return d


class ContinuidadeHF85(unittest.TestCase):
    def test_backup_antigo_alerta_sem_afirmar_integridade(self):
        r = diagnosticar_backups(
            {"ativo": True, "ultimo_backup_em": (NOW-timedelta(days=80)).isoformat()},
            [registro(24 * 80)], agora=NOW,
        )
        self.assertEqual(r["estado"], "atrasado")
        self.assertTrue(r["assinatura_registrada"])
        self.assertFalse(r["integridade_comprovada"])
        self.assertFalse(r["restauracao_comprovada"])
        self.assertNotIn("documentos", r)
        self.assertNotIn("NAO_PUBLICAR", str(r))

    def test_backup_recente_continua_sem_restauracao_comprovada(self):
        r = diagnosticar_backups(
            {"ativo": True, "ultimo_backup_em": (NOW-timedelta(hours=2)).isoformat()},
            [registro(2)], agora=NOW,
        )
        self.assertEqual(r["estado"], "recente_sem_restauracao_validada")
        self.assertTrue(r["requer_acao"])
        self.assertFalse(r["integridade_comprovada"])

    def test_agendamento_desligado(self):
        r = diagnosticar_backups({"ativo": False}, [registro()], agora=NOW)
        self.assertEqual(r["estado"], "agendamento_inativo")

    def test_registro_sem_data_e_desconhecido(self):
        r = diagnosticar_backups({"ativo": True}, [{"sha256": "a" * 64}], agora=NOW)
        self.assertEqual(r["estado"], "desconhecido")

    def test_sha_invalido_alerta(self):
        r = diagnosticar_backups({"ativo": True}, [registro(1, sha256="x")], agora=NOW)
        self.assertFalse(r["assinatura_registrada"])
        self.assertTrue(any("SHA-256" in x for x in r["motivos"]))

    def test_futuro_nao_e_backup_valido(self):
        r = diagnosticar_backups({"ativo": True}, [registro(-24)], agora=NOW)
        self.assertEqual(r["estado"], "desconhecido")

    def test_timezone_obrigatorio(self):
        with self.assertRaises(ValueError):
            diagnosticar_backups({}, [], agora=datetime(2026, 11, 28))

    def test_metadados_nao_vazam_documentos(self):
        meta = metadados_backup_registro(registro())
        self.assertNotIn("documentos", meta)
        self.assertEqual(set(meta), {"criado_em", "sha256", "tipo", "protegido"})


if __name__ == "__main__":
    unittest.main()
