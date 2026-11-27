"""HF72: testes inteiramente ficticios, sem banco ou mensagens."""
import copy
import unittest
from roteiro_diario_hf72 import roteiro_diario_hf72, texto_roteiro_hf72


class RoteiroHF72(unittest.TestCase):
    def test_ordem_e_omissao_de_etapas_vazias(self):
        resumo = {"conferencias": 3, "sem_registro_envio": 0,
                  "urgentes": 2, "altos": 1, "normais": 0}
        original = copy.deepcopy(resumo)
        r = roteiro_diario_hf72(resumo)
        self.assertEqual([x["Ordem"] for x in r], ["1", "3", "4"])
        self.assertEqual([x["Registros para conferir"] for x in r], [3, 2, 1])
        self.assertEqual(resumo, original)

    def test_dados_invalidos_nao_geram_pendencia(self):
        self.assertEqual(roteiro_diario_hf72(None), [])
        self.assertEqual(roteiro_diario_hf72({"urgentes": -3, "altos": "x"}), [])

    def test_exportacao_sem_identificadores_ou_contatos(self):
        resumo = {"conferencias": 1, "urgentes": 1,
                  "cliente": "Cliente Secreto", "whatsapp": "11999999999",
                  "numero_proposta": "PRIV-92873"}
        texto = texto_roteiro_hf72(roteiro_diario_hf72(resumo), "27/11/2026")
        for secreto in ("Cliente Secreto", "11999999999", "PRIV-92873"):
            self.assertNotIn(secreto, texto)
        self.assertIn("Revisar retornos urgentes", texto)

    def test_sem_tarefas(self):
        self.assertIn("Sem tarefas sinalizadas", texto_roteiro_hf72([], "27/11/2026"))


if __name__ == "__main__":
    unittest.main()
