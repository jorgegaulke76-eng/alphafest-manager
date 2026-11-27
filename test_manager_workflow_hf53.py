"""Comportamentos HF53 com dados fictícios; não importa app nem abre banco/rede."""
import copy
import ast
from datetime import date
from pathlib import Path
from types import SimpleNamespace
import unittest

import manager_workflow_hf53 as workflow
from catalogo_orcamento_service import ORCAMENTO_PRODUTO_LIVRE


HOJE = date(2026, 11, 25)
ITEM = {
    "produto": "Caneca", "quantidade": 2, "valor_unitario": 18.5,
    "especificacoes": "Tema: Espaço | Nome: Lia | Cor: azul",
    "produto_catalogo_id": "CAT-001", "produto_origem": "catalogo", "produto_digitado": "Caneca",
    "preco_especial_aplicado": True, "valor_base_oficial": 21.0, "abatimento_fixo_cliente": 2.5,
    "perfil_comercial_cliente_id": "CLIENTE-01", "projeto_id": "PRJ-01",
    "metadado_legado": {"acabamento": "fosco"},
}


class EdicaoItemTest(unittest.TestCase):
    def setUp(self):
        self.itens = [copy.deepcopy(ITEM), {"produto": "Topo", "quantidade": 1, "valor_unitario": 10}]
        self.antes = copy.deepcopy(self.itens)
        self.edicao = workflow.iniciar_edicao(self.itens, 0)

    def aplicar(self, **campos):
        valores = {k: self.itens[0].get(k) for k in ("produto", "quantidade", "valor_unitario", "especificacoes")}
        valores.update(campos)
        return workflow.aplicar_edicao(self.itens, self.edicao, **valores)

    def test_personalizacao_preserva_preco_cliente_e_todos_os_metadados(self):
        resultado = self.aplicar(especificacoes="Tema: Espaço | Nome: Ana | Cor: prata")
        esperado = copy.deepcopy(self.antes)
        esperado[0]["especificacoes"] = "Tema: Espaço | Nome: Ana | Cor: prata"
        self.assertEqual(resultado, esperado)
        self.assertEqual(len(resultado), 2)
        self.assertEqual(self.itens, self.antes)

    def test_quantidade_preserva_preco_combinado(self):
        resultado = self.aplicar(quantidade=4)
        self.assertEqual(resultado[0]["valor_unitario"], 18.5)
        self.assertEqual(resultado[0]["perfil_comercial_cliente_id"], "CLIENTE-01")
        self.assertEqual(resultado[0]["quantidade"] * resultado[0]["valor_unitario"], 74)

    def test_preco_legado_com_virgula_preserva_regra_ao_editar_detalhes(self):
        self.itens[0]["valor_unitario"] = "18,50"
        self.edicao = workflow.iniciar_edicao(self.itens, 0)
        resultado = self.aplicar(especificacoes="Novo nome", valor_unitario=18.5)
        self.assertTrue(resultado[0]["preco_especial_aplicado"])
        self.assertEqual(resultado[0]["perfil_comercial_cliente_id"], "CLIENTE-01")

    def test_cancelamento_nao_muda_item_cliente_ou_sessao(self):
        estado = {"temp_itens": self.itens, "form_cliente": "Cliente teste", "outro": [1], "editor": self.edicao}
        workflow.cancelar_edicao(estado, "editor")
        self.assertEqual(estado, {"temp_itens": self.antes, "form_cliente": "Cliente teste", "outro": [1]})

    def test_edicao_obsoleta_recusa_item_alterado_ou_removido(self):
        for itens in ([self.itens[1]], [dict(self.itens[0], quantidade=99)]):
            with self.subTest(itens=itens), self.assertRaisesRegex(ValueError, "mudou"):
                workflow.aplicar_edicao(itens, self.edicao, produto="Caneca", especificacoes="Nova", quantidade=2, valor_unitario=18.5)

    def test_preco_digitado_remove_apenas_calculo_comercial_antigo(self):
        novo = self.aplicar(valor_unitario=17)[0]
        self.assertFalse(set(workflow.SPECIAL_PRICE_FIELDS) & novo.keys())
        self.assertEqual(novo["produto_catalogo_id"], "CAT-001")
        self.assertEqual(novo["metadado_legado"], ITEM["metadado_legado"])

    def test_troca_explicita_produto_atualiza_identidade_sem_recalcular_preco(self):
        novo = self.aplicar(produto="Copo", catalogo_snapshot={"produto_catalogo_id": "CAT-02", "produto_origem": "catalogo", "produto_digitado": "Copo", "valor_unitario": 999})[0]
        self.assertEqual(novo["produto"], "Copo")
        self.assertEqual(novo["produto_catalogo_id"], "CAT-02")
        self.assertEqual(novo["valor_unitario"], 18.5)
        self.assertFalse(set(workflow.SPECIAL_PRICE_FIELDS) & novo.keys())

    def test_valores_invalidos_nao_mutam_lista(self):
        for campos in ({"quantidade": 0}, {"valor_unitario": -1}, {"quantidade": float("nan")}, {"produto": " "}):
            with self.subTest(campos=campos), self.assertRaises(ValueError):
                self.aplicar(**campos)
        self.assertEqual(self.itens, self.antes)


class AberturaFormularioTest(unittest.TestCase):
    def test_abertura_vazia_transfere_uma_vez_sem_herdar_vinculos(self):
        estado = {"temp_itens": [], "form_key": 4, "_projeto_origem_id": "ANTIGO", "alheio": {"x": 1}}
        dados = {"cliente": "Novo", "whatsapp": "000", "itens": [ITEM], "atendimento_id": "AT-01"}
        workflow.solicitar_abertura(estado, "novo_orcamento", dados)
        dados["itens"] = []
        resultado = workflow.resolver_abertura(estado, "abrir", hoje=HOJE)
        self.assertTrue(resultado["aplicado"])
        self.assertEqual(estado["form_cliente"], "Novo")
        self.assertEqual(estado["temp_itens"], [ITEM])
        self.assertEqual(estado["form_key"], 5)
        self.assertEqual(estado["_projeto_origem_id"], "")
        self.assertEqual(estado["_atendimento_origem_id"], "AT-01")
        antes_rerun = copy.deepcopy(estado)
        self.assertIsNone(workflow.resolver_abertura(estado, "substituir", hoje=HOJE))
        self.assertEqual(estado, antes_rerun)

    def test_rascunho_exige_escolha_e_cancelar_preserva_tudo(self):
        estado = {"temp_itens": [copy.deepcopy(ITEM)], "form_cliente": "Anterior", "editar_numero": "P-01"}
        antes = copy.deepcopy(estado)
        workflow.solicitar_abertura(estado, "novo_orcamento", {"cliente": "Novo"})
        with self.assertRaisesRegex(ValueError, "rascunho"):
            workflow.resolver_abertura(estado, "abrir", hoje=HOJE)
        workflow.resolver_abertura(estado, "cancelar", hoje=HOJE)
        self.assertEqual(estado, antes)

    def test_continuar_preserva_proposta_e_substituir_nao_acumula_itens(self):
        estado = {"temp_itens": [copy.deepcopy(ITEM)], "form_cliente": "Anterior", "editar_numero": "P-01", "form_documento": "DOC"}
        antes = copy.deepcopy(estado)
        workflow.solicitar_abertura(estado, "novo_orcamento", {"cliente": "Novo", "itens": [{"produto": "Novo"}]})
        resultado = workflow.resolver_abertura(estado, "continuar", hoje=HOJE)
        self.assertFalse(resultado["aplicado"])
        self.assertEqual(estado, antes)
        workflow.solicitar_abertura(estado, "novo_orcamento", {"cliente": "Novo", "itens": [{"produto": "Novo"}]})
        workflow.resolver_abertura(estado, "substituir", hoje=HOJE)
        self.assertEqual(estado["temp_itens"], [{"produto": "Novo"}])
        self.assertIsNone(estado["editar_numero"])
        self.assertEqual(estado["form_documento"], "")

    def test_projeto_prefill_e_rascunho_com_contexto_persistente(self):
        estado = {"hf53_projeto_necessidade": "Briefing anterior", "hf53_projeto_tema": "Azul"}
        workflow.solicitar_abertura(estado, "projeto", {"cliente": "Novo", "necessidade": "Bubble", "atendimento_id": "AT-02"})
        with self.assertRaises(ValueError):
            workflow.resolver_abertura(estado, "abrir", hoje=HOJE)
        workflow.resolver_abertura(estado, "substituir", hoje=HOJE)
        self.assertEqual(estado["hf53_projeto_necessidade"], "Bubble")
        self.assertEqual(estado["hf53_projeto_tema"], "")
        self.assertEqual(estado["_hf53_projeto_contexto"]["atendimento_id"], "AT-02")

    def test_modal_anna_isola_rascunho_e_origem_do_formulario_principal(self):
        estado = {"temp_itens": [ITEM], "form_cliente": "Jorge", "_atendimento_origem_id": "JORGE"}
        workflow.solicitar_abertura(estado, "novo_orcamento", {"cliente": "Anna", "itens": [ITEM], "atendimento_id": "ANNA"}, anna=True)
        workflow.resolver_abertura(estado, "abrir", hoje=HOJE)
        self.assertEqual(estado["form_cliente"], "Jorge")
        self.assertEqual(estado["_atendimento_origem_id"], "JORGE")
        self.assertEqual(estado["anna_modal_cliente"], "Anna")
        self.assertEqual(estado["_anna_hf53_atendimento_origem_id"], "ANNA")
        self.assertTrue(estado["anna_modal_iniciado_novo"])
        self.assertTrue(workflow.possui_rascunho(estado, "novo_orcamento", anna=True, hoje=HOJE))

    def test_formulario_em_branco_nao_e_rascunho_e_item_nao_adicionado_e_protegido(self):
        estado = {"form_key": 0, "form_entrega": HOJE, "produto_novo_0_catalogo": ORCAMENTO_PRODUTO_LIVRE}
        self.assertFalse(workflow.possui_rascunho(estado, "novo_orcamento", hoje=HOJE))
        estado["nome_item_0"] = "Lia"
        self.assertTrue(workflow.possui_rascunho(estado, "novo_orcamento", hoje=HOJE))
        self.assertIn("nome_item_0", workflow.chaves_rascunho(estado))

    def test_nome_personalizado_anna_sem_item_adicionado_tambem_e_rascunho(self):
        estado = {"anna_modal_iniciado_novo": True, "anna_modal_item_key": 3,
                  "anna_modal_itens": [], "anna_modal_entrega": HOJE,
                  "anna_modal_prod_3_catalogo": ORCAMENTO_PRODUTO_LIVRE,
                  "anna_modal_nome_item_3": "Lia"}
        self.assertTrue(workflow.possui_rascunho(estado, "novo_orcamento", anna=True, hoje=HOJE))
        workflow.solicitar_abertura(estado, "novo_orcamento", {"cliente": "Outro"}, anna=True)
        with self.assertRaises(ValueError):
            workflow.resolver_abertura(estado, "abrir", hoje=HOJE)
        self.assertEqual(estado["anna_modal_nome_item_3"], "Lia")
        self.assertEqual(estado["anna_modal_item_key"], 3)

    def test_pendente_nao_pode_ser_sobrescrita_silenciosamente(self):
        estado = {}
        workflow.solicitar_abertura(estado, "projeto", {"cliente": "A"})
        with self.assertRaises(ValueError):
            workflow.solicitar_abertura(estado, "projeto", {"cliente": "B"})
        self.assertEqual(estado[workflow.PENDING_KEY]["dados"]["cliente"], "A")


class ContextoModalAnnaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        arvore = ast.parse(Path(__file__).with_name("app.py").read_text(encoding="utf-8"))
        dialogo = next(n for n in arvore.body if isinstance(n, ast.FunctionDef) and n.name == "dialog_orcamento_anna")
        bloco = next(n for n in dialogo.body if isinstance(n, ast.If) and "_hf53_anna_contexto_formulario" in ast.unparse(n.test))
        cls.inicializacao = compile(ast.fix_missing_locations(ast.Module(body=[bloco], type_ignores=[])), "app.py:inicializacao_modal", "exec")

    def inicializar(self, estado, proposta):
        from datetime import datetime
        numero = proposta.get("numero_proposta")
        contexto = {"st": SimpleNamespace(session_state=estado), "proposta": proposta,
                    "chave_modal": f"anna_modal_iniciado_{numero or 'novo'}",
                    "cliente_prefixo_hf6": f"anna_orc_cliente_{numero or 'novo'}",
                    "valor_float": lambda v: float(v or 0), "datetime": datetime, "hoje_local": lambda: HOJE}
        exec(self.inicializacao, contexto)

    def test_reabrir_proposta_nao_usa_itens_ou_cliente_de_outra_janela(self):
        estado = {}
        primeira = {"numero_proposta": "P1", "cliente_nome": "Primeiro", "itens": [ITEM]}
        segunda = {"numero_proposta": "P2", "cliente_nome": "Segundo", "itens": [{"produto": "Topo", "quantidade": 1, "valor_unitario": 3}]}
        self.inicializar(estado, primeira)
        estado["_hf53_edicao_anna"] = workflow.iniciar_edicao(estado["anna_modal_itens"], 0)
        self.inicializar(estado, segunda)
        self.assertNotIn("_hf53_edicao_anna", estado)
        self.inicializar(estado, primeira)
        self.assertEqual(estado["anna_modal_cliente"], "Primeiro")
        self.assertEqual(estado["anna_modal_itens"], [ITEM])

    def test_inicializacao_modal_preserva_o_preenchimento_do_atalho(self):
        estado = {}
        workflow.solicitar_abertura(estado, "novo_orcamento", {"cliente": "Novo", "itens": [ITEM], "atendimento_id": "AT"}, anna=True)
        workflow.resolver_abertura(estado, "abrir", hoje=HOJE)
        self.inicializar(estado, {})
        self.assertEqual(estado["anna_modal_cliente"], "Novo")
        self.assertEqual(estado["anna_modal_itens"], [ITEM])
        self.assertEqual(estado["_anna_hf53_atendimento_origem_id"], "AT")


if __name__ == "__main__":
    unittest.main()
