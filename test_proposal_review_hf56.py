"""HF56: conferência comercial, cálculos independentes e assinatura do aceite.

Somente dados fictícios. A comparação com o Manager extrai uma função pura do
app por AST; não importa/inicia a aplicação, não acessa rede nem grava dados.
"""
import ast
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal, localcontext
from pathlib import Path
import random
import unittest

import proposal_review_service_hf56 as service


TODAY = date(2026, 11, 25)


def item(**changes):
    return {"produto": "Caneca personalizada", "quantidade": 2,
            "valor_unitario": 18.5, "especificacoes": "Nome: Ana", **changes}


def proposal(**changes):
    return {"cliente_nome": "Cliente de teste", "documento": "", "whatsapp": "11999999999",
            "itens": [item()], "subtotal": 37.0, "desconto": 2.0,
            "valor_total": 43.0, "taxa_entrega": 8.0, "frete_tipo": "Entrega",
            "data_entrega": "30/11/2026", "prazo_dias": "5", "validade_dias": "7",
            "_contexto_formulario": {"perfil": "jorge", "sequencia": 3}, **changes}


def review(data=None, **kwargs):
    return service.conferir_orcamento(proposal() if data is None else data, TODAY, **kwargs)


def codes(result, key="bloqueios"):
    return {entry["codigo"] for entry in result[key]}


def signature(data, **kwargs):
    return service.assinatura_revisao(data, review(data), **kwargs)


class ValuesAndCalculationTest(unittest.TestCase):
    def test_proposta_valida_com_entrega_e_desconto(self):
        result = review()
        self.assertTrue(result["pode_salvar"])
        self.assertEqual(result["bloqueios"], [])
        self.assertEqual(result["avisos"], [])
        self.assertEqual(result["resumo"], {
            "linhas": 1, "unidades": Decimal("2"), "subtotal": Decimal("37"),
            "desconto": Decimal("2"), "taxa_entrega": Decimal("8"), "valor_total": Decimal("43"),
            "itens": [{"indice": 0, "produto": "Caneca personalizada", "especificacoes": "Nome: Ana",
                       "quantidade": Decimal("2"), "valor_unitario": Decimal("18.5"), "total": Decimal("37")}],
        })

    def test_calculo_independente_nao_confia_nos_totais_informados(self):
        result = review(proposal(subtotal=123, valor_total=456))
        self.assertEqual(codes(result), {"subtotal_divergente", "valor_total_divergente"})
        self.assertFalse(result["pode_salvar"])
        self.assertEqual(result["resumo"]["subtotal"], Decimal("37"))
        self.assertEqual(result["resumo"]["valor_total"], Decimal("43"))

    def test_diferenca_de_um_centavo_exato_e_aceita(self):
        for difference in (Decimal("-0.01"), Decimal("0"), Decimal("0.01")):
            with self.subTest(difference=difference):
                result = review(proposal(subtotal=Decimal("37") + difference,
                                         valor_total=Decimal("43") + difference))
                self.assertTrue(result["pode_salvar"], result["bloqueios"])

    def test_diferenca_maior_que_um_centavo_bloqueia_sem_arredondar(self):
        for difference in (Decimal("-0.0100001"), Decimal("0.0100001")):
            with self.subTest(difference=difference):
                result = review(proposal(subtotal=Decimal("37") + difference,
                                         valor_total=Decimal("43") + difference))
                self.assertEqual(codes(result), {"subtotal_divergente", "valor_total_divergente"})

    def test_quantidades_fracionarias_legadas_permanecem_permitidas(self):
        for quantity in (1.5, Decimal("1.50"), "1,5", "1.5", "+1,5"):
            with self.subTest(quantity=quantity):
                result = review(proposal(itens=[item(quantidade=quantity)], subtotal=27.75, valor_total=33.75))
                self.assertTrue(result["pode_salvar"], result["bloqueios"])
                self.assertEqual(result["resumo"]["unidades"], Decimal("1.5"))

    def test_decimal_br_e_iso_sem_milhar(self):
        result = review(proposal(
            itens=[item(quantidade="2,0", valor_unitario="18,50")],
            subtotal="37.00", desconto="2,00", taxa_entrega="8.00", valor_total="43,00"))
        self.assertTrue(result["pode_salvar"])

    def test_strings_legadas_com_tres_casas_usam_ponto_decimal_como_manager(self):
        result = review(proposal(itens=[item(quantidade="2.000", valor_unitario="18.500")]))
        self.assertTrue(result["pode_salvar"], result["bloqueios"])
        self.assertEqual(result["resumo"]["subtotal"], Decimal("37.000000"))
        self.assertEqual(result["resumo"]["unidades"], Decimal("2.000"))

    def test_centavos_nao_sao_arredondados_por_linha(self):
        data = proposal(itens=[item(quantidade=1.5, valor_unitario="0.125")] * 2,
                        subtotal="0.3750", desconto=0, taxa_entrega=0,
                        frete_tipo="Retirada", valor_total="0.3750")
        result = review(data)
        self.assertTrue(result["pode_salvar"])
        self.assertEqual([row["total"] for row in result["resumo"]["itens"]], [Decimal("0.1875")] * 2)
        self.assertEqual(result["resumo"]["valor_total"], Decimal("0.375"))

    def test_precisao_do_chamador_nao_muda_calculo_ou_assinatura(self):
        data = proposal(itens=[item(quantidade=3, valor_unitario=Decimal("123456789.123456789"))],
                        subtotal=Decimal("370370367.370370367"), desconto=0,
                        taxa_entrega=0, frete_tipo="Retirada", valor_total=Decimal("370370367.370370367"))
        expected = review(data)
        expected_signature = signature(data)
        with localcontext() as context:
            context.prec = 2
            actual = review(data)
            self.assertEqual(context.prec, 2)
            self.assertEqual(actual, expected)
            self.assertEqual(signature(data), expected_signature)
        self.assertTrue(actual["pode_salvar"])

    def test_desconto_maior_que_subtotal_nao_e_limitado_silenciosamente(self):
        result = review(proposal(desconto=100, valor_total=8))
        self.assertIn("desconto_excedente", codes(result))
        self.assertIn("valor_total_divergente", codes(result))
        self.assertEqual(result["resumo"]["valor_total"], Decimal("-55"))

    def test_desconto_igual_ao_subtotal_e_permitido_com_aviso_total_zero(self):
        result = review(proposal(desconto=37, taxa_entrega=0, valor_total=0, frete_tipo="Retirada"))
        self.assertTrue(result["pode_salvar"])
        self.assertIn("total_zero", codes(result, "avisos"))

    def test_retirada_valida_tem_taxa_zero(self):
        result = review(proposal(frete_tipo="Retirada", taxa_entrega=0, valor_total=35))
        self.assertTrue(result["pode_salvar"])

    def test_retirada_com_taxa_nao_e_corrigida_silenciosamente(self):
        data = proposal(frete_tipo="Retirada")
        result = review(data)
        self.assertIn("taxa_retirada", codes(result))
        self.assertEqual(result["resumo"]["taxa_entrega"], Decimal("8"))
        self.assertEqual(data["taxa_entrega"], 8)


class InvalidInputsTest(unittest.TestCase):
    def test_cliente_vazio_ou_tipo_invalido_bloqueia(self):
        for name in (None, "", "   ", [], 123, False):
            with self.subTest(name=name):
                self.assertIn("cliente_vazio", codes(review(proposal(cliente_nome=name))))

    def test_lista_ausente_vazia_ou_invalida_bloqueia(self):
        for items, expected in (([], "sem_itens"), ((), "sem_itens"), (None, "itens_invalidos"),
                                ({}, "itens_invalidos"), ("Caneca", "itens_invalidos")):
            with self.subTest(items=items):
                result = review(proposal(itens=items))
                self.assertFalse(result["pode_salvar"])
                self.assertIn(expected, codes(result))

    def test_proposta_malformada_retorna_bloqueios_e_assina(self):
        for data in (None, [], "", 123, float("nan")):
            with self.subTest(data=repr(data)):
                result = service.conferir_orcamento(data, TODAY)
                self.assertIn("proposta_invalida", codes(result))
                self.assertFalse(result["pode_salvar"])
                self.assertEqual(len(service.assinatura_revisao(data, result)), 64)

    def test_todos_os_erros_de_todas_as_linhas_sao_apresentados(self):
        result = review(proposal(itens=[
            item(produto="", quantidade=0, valor_unitario=-1),
            None,
            item(produto=" ", quantidade=float("nan"), valor_unitario=float("inf")),
            item(quantidade=-4),
        ]))
        errors = {(entry["codigo"], entry.get("indice")) for entry in result["bloqueios"]}
        self.assertTrue({("produto_vazio", 0), ("quantidade_invalida", 0), ("preco_invalido", 0),
                         ("item_invalido", 1), ("produto_vazio", 2), ("quantidade_invalida", 2),
                         ("preco_invalido", 2), ("quantidade_invalida", 3)} <= errors)
        self.assertEqual(result["resumo"]["linhas"], 4)
        self.assertIsNone(result["resumo"]["subtotal"])
        self.assertIsNone(result["resumo"]["unidades"])

    def test_quantidades_invalidas_nao_sao_convertidas_para_zero_ou_um(self):
        for quantity in (None, "", "dois", 0, -1, True, False, {}, float("nan"), float("inf"),
                         Decimal("sNaN"), Decimal("-Infinity")):
            with self.subTest(quantity=repr(quantity)):
                result = review(proposal(itens=[item(quantidade=quantity)]))
                self.assertIn("quantidade_invalida", codes(result))
                self.assertIsNone(result["resumo"]["itens"][0]["quantidade"])

    def test_precos_invalidos_bloqueiam_sem_aviso_de_preco_zero(self):
        for price in (None, "", "R$ 18,50", -1, True, {}, float("nan"), float("-inf"),
                      Decimal("sNaN"), Decimal("Infinity")):
            with self.subTest(price=repr(price)):
                result = review(proposal(itens=[item(valor_unitario=price)]))
                self.assertIn("preco_invalido", codes(result))
                self.assertNotIn("preco_zero", codes(result, "avisos"))
                self.assertIsNone(result["resumo"]["valor_total"])

    def test_todos_os_valores_informados_exigem_numeros_finitos_nao_negativos(self):
        for field in ("subtotal", "desconto", "taxa_entrega", "valor_total"):
            for value in (None, "", "inválido", -1, True, [], float("nan"), float("inf"),
                          Decimal("sNaN"), Decimal("-Infinity")):
                with self.subTest(field=field, value=repr(value)):
                    result = review(proposal(**{field: value}))
                    self.assertIn(field + "_invalido", codes(result))
                    self.assertFalse(result["pode_salvar"])

    def test_numeros_agrupados_ou_com_unidades_nao_sao_adivinhados(self):
        for text in ("1.000,50", "1,000.50", "1 000", "1e3", "2 un.", "1,2,3"):
            with self.subTest(text=text):
                result = review(proposal(itens=[item(quantidade=text, valor_unitario=text)]))
                self.assertTrue({"quantidade_invalida", "preco_invalido"} <= codes(result))

    def test_valor_invalido_em_uma_linha_nao_mostra_soma_parcial_como_total(self):
        result = review(proposal(itens=[item(), item(valor_unitario="erro"), item()]))
        self.assertEqual(result["resumo"]["unidades"], Decimal("6"))
        self.assertIsNone(result["resumo"]["subtotal"])
        self.assertIsNone(result["resumo"]["valor_total"])
        self.assertEqual(len(result["resumo"]["itens"]), 3)

    def test_frete_desconhecido_nao_vira_retirada_ou_entrega(self):
        for frete in (None, "", "Correios", "Entrega ", "retirada", 1, []):
            with self.subTest(frete=frete):
                self.assertIn("frete_invalido", codes(review(proposal(frete_tipo=frete))))

    def test_expoentes_corrompidos_nao_causam_crash_ou_total_zero(self):
        for quantity, price in ((Decimal("1e999999"), Decimal("1e999999")),
                                (Decimal("1e-999999"), Decimal("1e-999999"))):
            with self.subTest(quantity=quantity):
                data = proposal(itens=[item(quantidade=quantity, valor_unitario=price)])
                result = review(data)
                self.assertFalse(result["pode_salvar"])
                self.assertIsNone(result["resumo"]["valor_total"])
                self.assertEqual(len(service.assinatura_revisao(data, result)), 64)


class WarningsAndDatesTest(unittest.TestCase):
    def test_preco_zero_exige_confirmacao_em_cada_linha(self):
        result = review(proposal(itens=[item(valor_unitario=0), item(valor_unitario=0)],
                                 subtotal=0, desconto=0, valor_total=8))
        self.assertTrue(result["pode_salvar"])
        warnings = [entry for entry in result["avisos"] if entry["codigo"] == "preco_zero"]
        self.assertEqual([entry["indice"] for entry in warnings], [0, 1])
        self.assertTrue(all(entry["exigir_confirmacao"] for entry in warnings))
        self.assertNotIn("total_zero", codes(result, "avisos"))

    def test_total_zero_exige_confirmacao(self):
        result = review(proposal(itens=[item(valor_unitario=0)], subtotal=0,
                                 desconto=0, taxa_entrega=0, valor_total=0))
        self.assertTrue(result["pode_salvar"])
        self.assertEqual(codes(result, "avisos"), {"preco_zero", "total_zero"})
        self.assertTrue(all(entry["exigir_confirmacao"] for entry in result["avisos"]))

    def test_total_informado_zero_exige_aceite_mesmo_dentro_da_tolerancia(self):
        result = review(proposal(itens=[item(quantidade=1, valor_unitario=0.01)],
                                subtotal=0.01, desconto=0, taxa_entrega=0,
                                valor_total=0, frete_tipo="Retirada"))
        self.assertTrue(result["pode_salvar"])
        self.assertEqual(result["resumo"]["valor_total"], Decimal("0.01"))
        self.assertEqual(codes(result, "avisos"), {"total_zero"})
        self.assertTrue(result["avisos"][0]["exigir_confirmacao"])

    def test_whatsapp_vazio_e_apenas_informativo_e_documento_nao_e_obrigatorio(self):
        for documento in ("", "CPF não informado", "123", None):
            with self.subTest(documento=documento):
                result = review(proposal(whatsapp="", documento=documento))
                self.assertTrue(result["pode_salvar"])
                self.assertEqual(codes(result, "avisos"), {"whatsapp_vazio"})
                self.assertFalse(result["avisos"][0]["exigir_confirmacao"])

    def test_datas_validas_br_iso_e_date(self):
        for delivery in ("25/11/2026", "2026-11-25", TODAY, datetime(2026, 11, 25, 23, 30)):
            with self.subTest(delivery=delivery):
                result = review(proposal(data_entrega=delivery))
                self.assertTrue(result["pode_salvar"])
                self.assertNotIn("entrega_passada", codes(result, "avisos"))

    def test_data_invalida_ou_ausente_bloqueia_inclusive_edicao(self):
        for delivery in (None, "", "31/11/2026", "29/02/2026", "11/30/2026", "amanhã", 20261130):
            for edit in (False, True):
                with self.subTest(delivery=delivery, edit=edit):
                    self.assertIn("data_entrega_invalida", codes(review(proposal(data_entrega=delivery), em_edicao=edit)))

    def test_data_passada_precisa_aceite_so_em_novo_orcamento(self):
        data = proposal(data_entrega="24/11/2026")
        new = review(data)
        self.assertTrue(new["pode_salvar"])
        warning = next(entry for entry in new["avisos"] if entry["codigo"] == "entrega_passada")
        self.assertTrue(warning["exigir_confirmacao"])
        edited = review(data, em_edicao=True)
        self.assertTrue(edited["pode_salvar"])
        self.assertNotIn("entrega_passada", codes(edited, "avisos"))

    def test_data_referencia_invalida_bloqueia_sem_consultar_relogio(self):
        result = service.conferir_orcamento(proposal(), "hoje")
        self.assertIn("data_referencia_invalida", codes(result))

    def test_prazos_ausentes_textuais_fracionarios_ou_invalidos_exigem_aceite(self):
        for value in (None, "", "a combinar", 0, -1, 1.5, "1,5", True, float("nan"), float("inf")):
            with self.subTest(value=repr(value)):
                data = proposal(prazo_dias=value, validade_dias=value)
                result = review(data)
                self.assertTrue(result["pode_salvar"])
                self.assertTrue({"prazo_dias_pendente", "validade_dias_pendente"} <= codes(result, "avisos"))
                self.assertTrue(all(entry["exigir_confirmacao"] for entry in result["avisos"]))
                self.assertIs(data["prazo_dias"], value)

    def test_prazos_inteiros_positivos_nao_exigem_aceite(self):
        for value in (1, 5.0, Decimal("7.0"), "10", "10,0", "10.0"):
            with self.subTest(value=value):
                self.assertFalse(review(proposal(prazo_dias=value, validade_dias=value))["avisos"])

    def test_item_pendente_nao_e_adicionado_automaticamente(self):
        data = proposal()
        before = deepcopy(data)
        result = review(data, item_pendente=True)
        warning = next(entry for entry in result["avisos"] if entry["codigo"] == "item_pendente")
        self.assertTrue(warning["exigir_confirmacao"])
        self.assertIn("produto selecionado", warning["mensagem"])
        self.assertIn("confirmados", warning["mensagem"])
        self.assertNotIn("digitado", warning["mensagem"])
        self.assertEqual(data, before)
        self.assertEqual(result["resumo"]["linhas"], 1)


class SignatureAndPreservationTest(unittest.TestCase):
    def test_conferencia_nao_muta_payload_nem_metadata(self):
        data = proposal(itens=[item(produto="  Caneca  ", especificacoes="Nome: Ana\n\nCor: azul ",
                                    produto_catalogo_id="CAT-1", produto_origem="catalogo_alias",
                                    preco_especial_aplicado=True, preco_base=20,
                                    metadata={"mensagem": ["original", {"nota": "não apagar"}]})])
        before = deepcopy(data)
        result = review(data)
        service.assinatura_revisao(data, result, contexto={"perfil": "jorge"})
        self.assertEqual(data, before)
        self.assertEqual(result["resumo"]["itens"][0]["produto"], "  Caneca  ")
        self.assertEqual(result["resumo"]["itens"][0]["especificacoes"], "Nome: Ana\n\nCor: azul ")

    def test_assinatura_estavel_com_chaves_reordenadas_em_todos_os_niveis(self):
        def reverse(value):
            if isinstance(value, dict):
                return {key: reverse(item) for key, item in reversed(list(value.items()))}
            if isinstance(value, list):
                return [reverse(item) for item in value]
            return value
        data = proposal()
        result = review(data)
        self.assertEqual(service.assinatura_revisao(data, result, contexto={"a": 1, "b": 2}),
                         service.assinatura_revisao(reverse(data), reverse(result), contexto={"b": 2, "a": 1}))

    def test_assinatura_inclui_preco_prazos_datas_cliente_e_campos_adicionais(self):
        data = proposal()
        expected = signature(data)
        for field, value in (("cliente_nome", "Outro cliente"), ("documento", "123"), ("whatsapp", "21999999999"),
                             ("data_entrega", "01/12/2026"), ("prazo_dias", "6"), ("validade_dias", "8"),
                             ("subtotal", 38), ("valor_total", 44), ("desconto", 3), ("taxa_entrega", 9),
                             ("briefing_origem", "Mensagem original"), ("novo_metadado", {"valor": 1})):
            with self.subTest(field=field):
                changed = deepcopy(data)
                changed[field] = value
                self.assertNotEqual(expected, signature(changed))
        for field, value in (("valor_unitario", 19), ("quantidade", 3), ("especificacoes", "Nome: Bia"),
                             ("produto_catalogo_id", "CAT-2"), ("preco_especial_aplicado", True)):
            with self.subTest(item_field=field):
                changed = deepcopy(data)
                changed["itens"][0][field] = value
                self.assertNotEqual(expected, signature(changed))

    def test_assinatura_inclui_contexto_de_formulario_e_contexto_externo(self):
        data = proposal()
        expected = signature(data, contexto={"perfil": "jorge", "edicao": False})
        self.assertNotEqual(expected, signature(data, contexto={"perfil": "anna", "edicao": False}))
        self.assertNotEqual(expected, signature(data, contexto={"perfil": "jorge", "edicao": True}))
        changed = deepcopy(data)
        changed["_contexto_formulario"]["sequencia"] += 1
        self.assertNotEqual(signature(data), signature(changed))

    def test_assinatura_inclui_avisos_bloqueios_e_resultado_calculado(self):
        data = proposal()
        result = review(data)
        expected = service.assinatura_revisao(data, result)
        pending = review(data, item_pendente=True)
        self.assertNotEqual(expected, service.assinatura_revisao(data, pending))
        for key, value in (("bloqueios", [{"codigo": "x", "mensagem": "x"}]), ("pode_salvar", False),
                           ("resumo", {"valor_total": Decimal("1")})):
            changed = deepcopy(result)
            changed[key] = value
            self.assertNotEqual(expected, service.assinatura_revisao(data, changed))

    def test_assinatura_distingue_ordem_multiplicidade_e_personalizacao_de_linhas(self):
        data = proposal(itens=[item(especificacoes="Ana"), item(especificacoes="Bia")])
        expected = signature(data)
        changed = deepcopy(data)
        changed["itens"].reverse()
        self.assertNotEqual(expected, signature(changed))
        changed = deepcopy(data)
        changed["itens"].append(deepcopy(changed["itens"][0]))
        self.assertNotEqual(expected, signature(changed))

    def test_nan_infinito_e_snan_bloqueiam_e_possuem_assinaturas_estaveis(self):
        signatures = []
        for value in (float("nan"), float("inf"), float("-inf"), Decimal("sNaN")):
            data = proposal(itens=[item(valor_unitario=value)])
            result = review(data)
            self.assertIn("preco_invalido", codes(result))
            first = service.assinatura_revisao(data, result)
            self.assertEqual(first, service.assinatura_revisao(deepcopy(data), deepcopy(result)))
            signatures.append(first)
        self.assertEqual(len(set(signatures)), 4)

    def test_assinatura_suporta_metadata_invalido_e_referencia_circular(self):
        data = proposal(metadata={"valor": Decimal("1e999999"), "nao_finito": float("nan"),
                                  "bytes": b"x", "conjunto": {"a", "b"}})
        data["referencia"] = data
        result = review(data)
        self.assertEqual(service.assinatura_revisao(data, result), service.assinatura_revisao(data, result))


class ExistingFlowsTest(unittest.TestCase):
    def test_importacao_real_hf54_preserva_personalizacoes_e_metadata(self):
        import site_quote_import_service as importer
        source = "1. Caneca\nQuantidade: 2\nPersonalização/observações: Nome: Ana\n\n2. Caneca\nQuantidade: 1\nPersonalização/observações: Nome: Bia"
        analysis = importer.analisar_mensagem(source, [{"Nome": "Caneca", "CatalogoId": "CAT-1", "Preco": 18.5}])
        draft = importer.preparar_rascunho(analysis, deepcopy(analysis["itens"]))
        data = proposal(itens=draft["itens"], subtotal=55.5, valor_total=61.5,
                        briefing_origem=draft["observacoes"])
        before = deepcopy(data)
        result = review(data)
        self.assertTrue(result["pode_salvar"], result["bloqueios"])
        self.assertEqual(result["resumo"]["linhas"], 2)
        self.assertEqual(result["resumo"]["unidades"], Decimal("3"))
        self.assertEqual([row["especificacoes"] for row in result["resumo"]["itens"]], ["Nome: Ana", "Nome: Bia"])
        self.assertEqual(data, before)
        self.assertEqual([row["produto_catalogo_id"] for row in data["itens"]], ["CAT-1", "CAT-1"])

    def test_preco_zero_confirmado_no_importador_exige_nova_conferencia_ao_salvar(self):
        import site_quote_import_service as importer
        analysis = importer.analisar_mensagem("1. Produto livre\nQuantidade: 1", [])
        draft = importer.preparar_rascunho(analysis, analysis["itens"], confirmar_sem_preco=True)
        result = review(proposal(itens=draft["itens"], subtotal=0, desconto=0, valor_total=8))
        self.assertTrue(result["pode_salvar"])
        self.assertIn("preco_zero", codes(result, "avisos"))
        self.assertTrue(next(entry for entry in result["avisos"] if entry["codigo"] == "preco_zero")["exigir_confirmacao"])

    def test_edicao_historica_mantem_demais_bloqueios_e_avisos(self):
        data = proposal(data_entrega="01/01/2020", itens=[item(valor_unitario=0)], subtotal=0,
                        desconto=0, valor_total=8, prazo_dias="a combinar")
        result = review(data, em_edicao=True, item_pendente=True)
        self.assertTrue(result["pode_salvar"])
        self.assertTrue({"preco_zero", "prazo_dias_pendente", "item_pendente"} <= codes(result, "avisos"))
        self.assertNotIn("entrega_passada", codes(result, "avisos"))
        data["itens"][0]["quantidade"] = 0
        self.assertFalse(review(data, em_edicao=True)["pode_salvar"])

    def test_calculo_coincide_com_funcao_real_do_app_para_orcamentos_validos(self):
        tree = ast.parse(Path(__file__).with_name("app.py").read_text(encoding="utf-8"))
        functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
        environment = {}
        module = ast.Module(body=[deepcopy(functions[name]) for name in ("valor_float", "calcular_valores_proposta")], type_ignores=[])
        exec(compile(ast.fix_missing_locations(module), "app.py", "exec"), environment)
        rng = random.Random(56)
        for _ in range(50):
            items = [item(quantidade=rng.randint(1, 100) / 4, valor_unitario=rng.randint(0, 20000) / 100)
                     for _ in range(rng.randint(1, 10))]
            subtotal = sum(row["quantidade"] * row["valor_unitario"] for row in items)
            discount = round(subtotal * rng.random() / 2, 2)
            fee = rng.randint(0, 3000) / 100
            data = proposal(itens=items, desconto=discount, taxa_entrega=fee)
            data.pop("valor_total")
            actual_subtotal, _, actual_total = environment["calcular_valores_proposta"](data)
            data.update(subtotal=actual_subtotal, valor_total=actual_total)
            result = review(data)
            self.assertTrue(result["pode_salvar"], result["bloqueios"])
            self.assertAlmostEqual(float(result["resumo"]["subtotal"]), actual_subtotal, places=7)
            self.assertAlmostEqual(float(result["resumo"]["valor_total"]), actual_total, places=7)


if __name__ == "__main__":
    unittest.main()
