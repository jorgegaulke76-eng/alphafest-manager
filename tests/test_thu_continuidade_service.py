import unittest
from datetime import date

from thu_continuidade_service import montar_sinais_sem_avanco


class ThuContinuidadeServiceTests(unittest.TestCase):
    def linha(self, numero="P1", status="Aprovado · Pago", entrega="02/09/2026", **extra):
        base = {
            "numero_proposta": numero,
            "status": status,
            "cliente_nome": f"Cliente {numero}",
            "telefone": "11999990000",
            "produtos": "1× Produto",
            "data_entrega": entrega,
        }
        base.update(extra)
        return base

    def snapshot(self, *linhas):
        return {"registrado_em": "2026-09-02T08:00:00", "linhas": list(linhas)}

    def test_prazo_hoje_mesma_fase_desde_manha_gera_sinal_imediato(self):
        hoje = date(2026, 9, 2)
        atual = self.linha("HOJE", status="Entrega hoje · Aprovado · Pago", entrega="02/09/2026")
        snapshots = {"2026-09-02": self.snapshot(self.linha("HOJE", status="Entrega hoje · Aprovado · Pago"))}
        sinais = montar_sinais_sem_avanco([atual], snapshots, hoje)
        self.assertEqual(len(sinais), 1)
        self.assertEqual(sinais[0]["nivel"], "urgente")
        self.assertIn("desde a abertura", sinais[0]["motivo"])
        self.assertIn("produção", sinais[0]["acao"].lower())

    def test_entrega_futura_com_apenas_snapshot_de_hoje_nao_polui_bloco(self):
        hoje = date(2026, 9, 2)
        atual = self.linha("FUT", entrega="20/09/2026")
        snapshots = {"2026-09-02": self.snapshot(atual)}
        self.assertEqual(montar_sinais_sem_avanco([atual], snapshots, hoje), [])

    def test_mesma_fase_por_dois_dias_gera_sinal_mesmo_com_entrega_futura(self):
        hoje = date(2026, 9, 4)
        linha = self.linha("PERSISTE", entrega="20/09/2026")
        snapshots = {
            "2026-09-02": self.snapshot(linha),
            "2026-09-03": self.snapshot(linha),
            "2026-09-04": self.snapshot(linha),
        }
        sinais = montar_sinais_sem_avanco([linha], snapshots, hoje)
        self.assertEqual(len(sinais), 1)
        self.assertEqual(sinais[0]["dias_mesma_fase"], 2)
        self.assertIn("2 dia(s)", sinais[0]["motivo"])

    def test_mudanca_de_fase_quebra_contagem(self):
        hoje = date(2026, 9, 4)
        atual = self.linha("MUDOU", status="Pronto / aguardando retirada ou entrega · Pago", entrega="20/09/2026")
        snapshots = {
            "2026-09-02": self.snapshot(self.linha("MUDOU", status="Aprovado · Pago", entrega="20/09/2026")),
            "2026-09-03": self.snapshot(self.linha("MUDOU", status="Aprovado · Pago", entrega="20/09/2026")),
            "2026-09-04": self.snapshot(atual),
        }
        self.assertEqual(montar_sinais_sem_avanco([atual], snapshots, hoje), [])

    def test_prefixo_atrasado_nao_e_mudanca_de_fase(self):
        hoje = date(2026, 9, 3)
        atual = self.linha("ATR", status="ATRASADO · Aprovado · Pago", entrega="01/09/2026")
        snapshots = {
            "2026-09-02": self.snapshot(self.linha("ATR", status="ATRASADO · Aprovado · Pago", entrega="01/09/2026")),
            "2026-09-03": self.snapshot(atual),
        }
        sinais = montar_sinais_sem_avanco([atual], snapshots, hoje)
        self.assertEqual(len(sinais), 1)
        self.assertEqual(sinais[0]["fase"], "aprovado_pago")

    def test_pronto_vencido_sugere_saida_e_nao_producao(self):
        hoje = date(2026, 9, 3)
        atual = self.linha("PR", status="SAÍDA ATRASADA · Pronto / aguardando retirada ou entrega · Pago", entrega="02/09/2026")
        snapshots = {"2026-09-03": self.snapshot(atual)}
        sinais = montar_sinais_sem_avanco([atual], snapshots, hoje)
        self.assertEqual(len(sinais), 1)
        self.assertEqual(sinais[0]["fase"], "pronto")
        self.assertIn("retirada/entrega", sinais[0]["acao"])

    def test_aguardando_aprovacao_vencida_sugere_confirmar_cliente(self):
        hoje = date(2026, 9, 3)
        atual = self.linha("APR", status="Prazo vencido · Aguardando aprovação", entrega="02/09/2026")
        snapshots = {"2026-09-03": self.snapshot(atual)}
        sinais = montar_sinais_sem_avanco([atual], snapshots, hoje)
        self.assertEqual(len(sinais), 1)
        self.assertIn("cliente", sinais[0]["acao"].lower())

    def test_limite_e_prioridade(self):
        hoje = date(2026, 9, 3)
        a = self.linha("A", status="ATRASADO · Aprovado · Pago", entrega="01/09/2026")
        b = self.linha("B", status="Entrega hoje · Aprovado · Pago", entrega="03/09/2026")
        snapshots = {"2026-09-03": self.snapshot(a, b)}
        sinais = montar_sinais_sem_avanco([b, a], snapshots, hoje, limite=1)
        self.assertEqual([x["numero_proposta"] for x in sinais], ["A"])


if __name__ == "__main__":
    unittest.main()
