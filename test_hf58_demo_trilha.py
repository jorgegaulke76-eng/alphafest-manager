"""Transições demonstrativas sem banco, navegador ou armazenamento externo."""
from __future__ import annotations

import unittest
from datetime import datetime

from ficha_producao_hf58 import registrar_mutacao_arte, registrar_aprovacao, situacao_arte
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / ".github" / "homologacao_hf58"))
from trilha_hf58 import adicionar_transicao, relatorio_trilha_txt


def arquivo(ident, nome, url):
    return {
        "id": ident, "nome": nome, "categoria": "Arte",
        "arquivado": False, "url": url, "criado_em": "2026-11-25T19:00:00",
    }


class TrilhaDemoHF58Tests(unittest.TestCase):
    def cadeia(self, nome_repetido=False):
        t = datetime(2026, 11, 25, 19, 30)
        base = {"id": "DEMO", "arquivos": [], "aprovacao_arte_hf58": {}}
        v1 = registrar_mutacao_arte(
            {**base, "arquivos": [arquivo("AR1", "arte.png" if nome_repetido else "v1.png", "https://exemplo.invalid/a")]},
            token="V1",
        )
        aprovado_v1 = registrar_aprovacao(v1, "AR1", "Jorge", t)
        v2 = registrar_mutacao_arte(
            {**aprovado_v1, "arquivos": v1["arquivos"] + [arquivo("AR2", "arte.png" if nome_repetido else "v2.png", "https://exemplo.invalid/b")]},
            token="V2",
        )
        aprovado_v2 = registrar_aprovacao(v2, "AR2", "Anna", t)
        return (base, v1, aprovado_v1, v2, aprovado_v2), t

    def test_trilha_completa_preserva_revisao_pendente(self):
        estados, instante = self.cadeia()
        trilha = []
        for seq in range(1, 5):
            trilha = adicionar_transicao(
                trilha, estados[seq - 1], estados[seq],
                passo=seq, perfil="Anna", instante=instante
            )
        self.assertEqual(
            [(e["Antes"], e["Depois"]) for e in trilha],
            [
                ("sem_arte", "sem_aprovacao"),
                ("sem_aprovacao", "aprovada"),
                ("aprovada", "revisao_pendente"),
                ("revisao_pendente", "aprovada"),
            ]
        )
        self.assertEqual(situacao_arte(estados[-1])[0], "aprovada")
        txt = relatorio_trilha_txt(trilha).decode("utf-8-sig")
        self.assertIn("aprovada -> revisao_pendente", txt)
        self.assertIn("revisao_pendente -> aprovada", txt)

    def test_mesmo_nome_ainda_registra_pendencia_por_novo_id(self):
        estados, instante = self.cadeia(nome_repetido=True)
        self.assertEqual(estados[1]["arquivos"][0]["nome"], estados[3]["arquivos"][1]["nome"])
        self.assertEqual(situacao_arte(estados[3])[0], "revisao_pendente")
        trilha = adicionar_transicao([], estados[2], estados[3], passo=3, perfil="Jorge", instante=instante)
        self.assertEqual(trilha[0]["Antes"], "aprovada")
        self.assertEqual(trilha[0]["Depois"], "revisao_pendente")
        self.assertEqual(trilha[0]["ID"], "AR2")

    def test_sem_mudanca_de_estado_nao_polui_historico(self):
        estados, instante = self.cadeia()
        t = adicionar_transicao([], estados[1], estados[1], passo=9, perfil="Anna", instante=instante)
        self.assertEqual(t, [])

    def test_relatorio_continua_identificado_como_ficticio(self):
        texto = relatorio_trilha_txt([]).decode("utf-8-sig")
        self.assertIn("FICTICIA", texto)
        self.assertIn("NAO EVIDENCIA DE BANCO", texto)


if __name__ == "__main__":
    unittest.main()
