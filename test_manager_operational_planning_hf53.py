"""Planos protegidos da Anna com pedidos fictícios e engines reais, offline."""
import copy
from datetime import date
import unittest

from central_operational_runtime import montar_snapshot_operacional
from central_producao_painel_hf41 import preparar_fila
from manager_operational_planning_hf53 import montar_planejamentos, renderizar_planejamentos, OPERATIONAL_FIELDS
from pedido_resumo import resumo_produtos_pedido
from planejamento_diario_hf49 import plano_diario
from planejamento_semanal_hf48 import planejar
from roteiro_producao_hf51 import roteiro_diario, agenda_semanal_csv


class FakeUI:
    def __init__(self):
        self.downloads = []
        self.pressed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def expander(self, *args, **kwargs):
        return self

    def columns(self, widths):
        return [self] * (widths if isinstance(widths, int) else len(widths))

    def selectbox(self, label, options, **kwargs):
        return list(options)[0]

    def text_input(self, *args, **kwargs):
        return ""

    def number_input(self, *args, **kwargs):
        return 1

    def button(self, label, **kwargs):
        if not self.pressed and label == "Abrir pedido":
            self.pressed = True
            return True
        return False

    def download_button(self, label, **kwargs):
        self.downloads.append(kwargs)

    def __getattr__(self, name):
        if name in {"caption", "metric", "info", "write", "success", "dataframe"}:
            return lambda *args, **kwargs: None
        raise AttributeError(name)


class PlanosAnnaTest(unittest.TestCase):
    def setUp(self):
        self.hoje = date(2026, 11, 25)
        base = dict(cliente_nome="Cliente teste", aprovado=True, whatsapp="TELEFONE_PRIVADO",
                    valor_total="VALOR_PRIVADO", pagamento="REGRA_PRIVADA", documento="DOCUMENTO_PRIVADO",
                    itens=[{"produto": "Caneca", "quantidade": 3, "valor_unitario": 20}])
        self.propostas = [
            dict(base, numero_proposta="A", data_entrega="24/11/2026"),
            dict(base, numero_proposta="B", data_entrega="25/11/2026", pronto=True),
            dict(base, numero_proposta="C", data_entrega=""),
            dict(base, numero_proposta="D", data_entrega="25/11/2026", aprovado=False),
            dict(base, numero_proposta="E", data_entrega="25/11/2026", entregue=True),
            dict(base, numero_proposta="F", data_entrega="25/11/2026", cancelado_cliente=True),
            dict(base, numero_proposta="G", data_entrega="02/12/2026"),
        ]
        self.propostas.append(copy.deepcopy(self.propostas[1]))
        self.tarefas = [
            {"numero_proposta": "A", "status": "Em produção"},
            {"numero_proposta": "B", "status": "Arte pendente"},
            {"numero_proposta": "C", "status": "Em produção", "ativa": False},
        ]

    def test_mesma_fonte_oficial_deduplicada_status_e_prazo(self):
        planos = montar_planejamentos(self.propostas, self.tarefas, self.hoje)
        grupos = planos["diario"]["grupos"]
        self.assertEqual({p["numero_proposta"] for itens in grupos.values() for p in itens}, {"A", "B", "C", "G"})
        self.assertEqual(sum(map(len, grupos.values())), 4)
        self.assertEqual(grupos["Hoje"][0]["fase_hf41"], "pronto_entrega")
        self.assertEqual(grupos["Hoje"][0]["acao_hf49"], "Combinar retirada/entrega")
        self.assertEqual(grupos["Sem prazo"][0]["fase_hf41"], "sem_registro")
        self.assertEqual(planos["semanal"]["total_semana"], 1)
        self.assertEqual(len(planos["semanal"]["fora_periodo"]), 1)

    def test_resultado_reutiliza_as_engines_existentes_sem_regras_paralelas(self):
        snapshot = montar_snapshot_operacional(self.propostas, self.tarefas, [], {}, [], self.hoje,
                                               resumo_produtos=resumo_produtos_pedido, sob_encomenda=True)
        fila = [{campo: p.get(campo) for campo in OPERATIONAL_FIELDS}
                for p in preparar_fila(snapshot["central_producao"], hoje=self.hoje)]
        planos = montar_planejamentos(self.propostas, self.tarefas, self.hoje)
        self.assertEqual(planos["diario"], plano_diario(fila, hoje=self.hoje))
        self.assertEqual(planos["semanal"], planejar(fila, hoje=self.hoje))

    def test_planos_e_downloads_so_contem_dados_operacionais_e_nao_mutam_fontes(self):
        antes = copy.deepcopy((self.propostas, self.tarefas))
        planos = montar_planejamentos(self.propostas, self.tarefas, self.hoje)
        txt = roteiro_diario(planos["diario"], incluir_retornos=False)
        csv = agenda_semanal_csv(planos["semanal"]).decode("utf-8-sig")
        for privado in ("TELEFONE_PRIVADO", "VALOR_PRIVADO", "REGRA_PRIVADA", "DOCUMENTO_PRIVADO", "RETORNOS COMERCIAIS"):
            self.assertNotIn(privado, repr(planos) + txt + csv)
        permitidos = set(OPERATIONAL_FIELDS) | {"grupo_hf49", "acao_hf49"}
        for grupo in planos["diario"]["grupos"].values():
            for pedido in grupo:
                self.assertLessEqual(set(pedido), permitidos)
        self.assertEqual((self.propostas, self.tarefas), antes)

    def test_componente_abre_pedido_e_exporta_a_mesma_fotografia(self):
        planos = montar_planejamentos(self.propostas, self.tarefas, self.hoje)
        ui, abertos = FakeUI(), []
        renderizar_planejamentos(ui, planos, abertos.append)
        self.assertEqual(abertos, ["A"])
        self.assertEqual(len(ui.downloads), 2)
        self.assertEqual(ui.downloads[0]["data"], roteiro_diario(planos["diario"], incluir_retornos=False).encode("utf-8"))
        self.assertEqual(ui.downloads[1]["data"], agenda_semanal_csv(planos["semanal"]))
        self.assertNotIn(b"RETORNOS COMERCIAIS", ui.downloads[0]["data"])


if __name__ == "__main__":
    unittest.main()
