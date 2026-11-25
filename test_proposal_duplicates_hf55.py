"""HF55: conferência pura de possíveis repetidos, apenas dados fictícios."""
from copy import deepcopy
from datetime import date, datetime, timedelta
from decimal import Decimal
import json
import unittest

import proposal_duplicate_service_hf55 as service


TODAY = date(2026, 11, 25)


def item(nome="Caneca Personalizada", quantidade=1, nota="Nome: Ana", **extra):
    return {
        "produto": nome, "quantidade": quantidade, "especificacoes": nota,
        "valor_unitario": 18.5, **extra,
    }


def proposal(**extra):
    return {
        "cliente_nome": "Cliente de teste", "whatsapp": "(11) 98765-4321",
        "documento": "", "relacionamento_id": "", "itens": [item()],
        "evento": "Aniversário", "data_entrega": "30/11/2026",
        "briefing_origem": "", "subtotal": 18.5, "valor_total": 18.5,
        "_contexto_formulario": "form-1", **extra,
    }


def historic(**extra):
    data = proposal(**{"numero_proposta": "PROP-TESTE-01", "data_geracao": "25/11/2026", "aprovado": False, **extra})
    data.pop("_contexto_formulario", None)
    return data


def analyze(new=None, history=None, **kwargs):
    return service.analisar_duplicidades(
        proposal() if new is None else new,
        [historic()] if history is None else history,
        TODAY, **kwargs,
    )


class IdentityTest(unittest.TestCase):
    def test_mesmo_whatsapp_identifica_mesmo_com_nome_diferente(self):
        result = analyze(history=[historic(cliente_nome="Nome comercial atualizado")])
        candidate = result["candidatos"][0]
        self.assertEqual(candidate["identidade"], "whatsapp")
        self.assertEqual(candidate["correspondencias"], ["itens"])

    def test_ddi_55_local_e_formato_internacional_equivalem(self):
        for phone in ("+55 (11) 98765-4321", "5511987654321", "0055 11 98765-4321", "11987654321"):
            with self.subTest(phone=phone):
                self.assertEqual(len(analyze(history=[historic(whatsapp=phone)])["candidatos"]), 1)

    def test_ddd_55_local_nao_e_removido_e_nono_digito_nao_e_inventado(self):
        new = proposal(whatsapp="55987654321")
        self.assertEqual(len(analyze(new, [historic(whatsapp="+55 55 98765-4321")])["candidatos"]), 1)
        self.assertFalse(analyze(new, [historic(whatsapp="55 8765-4321")])["candidatos"])
        self.assertFalse(analyze(history=[historic(whatsapp="11 8765-4321")])["candidatos"])

    def test_homonimos_com_telefone_contraditorio_nao_sao_candidatos(self):
        self.assertFalse(analyze(history=[historic(whatsapp="21987654321")])["candidatos"])

    def test_documentos_contraditorios_bloqueiam_telefone_igual(self):
        new = proposal(documento="123.456.789-09")
        old = historic(documento="987.654.321-00")
        self.assertFalse(analyze(new, [old])["candidatos"])

    def test_telefones_contraditorios_bloqueiam_documento_igual(self):
        new = proposal(documento="123.456.789-09")
        old = historic(documento="12345678909", whatsapp="21987654321")
        self.assertFalse(analyze(new, [old])["candidatos"])

    def test_identificador_malformado_nao_esconde_contradicao(self):
        new = proposal(documento="123.456.789-09")
        self.assertFalse(analyze(new, [historic(documento="987")])["candidatos"])
        self.assertFalse(analyze(new, [historic(documento="12345678909", whatsapp="219876543")])["candidatos"])

    def test_documento_igual_formatado_sem_telefone(self):
        new = proposal(documento="123.456.789-09", whatsapp="")
        old = historic(documento="12345678909", whatsapp="")
        self.assertEqual(analyze(new, [old])["candidatos"][0]["identidade"], "documento")

    def test_relacionamento_existente_e_evidencia_sem_inventar_identificador(self):
        new = proposal(cliente_nome="", whatsapp="", relacionamento_id="REL-TESTE-1")
        old = historic(cliente_nome="", whatsapp="", relacionamento_id="REL-TESTE-1")
        self.assertEqual(analyze(new, [old])["candidatos"][0]["identidade"], "relacionamento")
        old["relacionamento_id"] = "REL-TESTE-2"
        self.assertFalse(analyze(new, [old])["candidatos"])

    def test_aliases_reais_do_cadastro_legado(self):
        old = historic()
        old["cliente"] = old.pop("cliente_nome")
        old["cliente_wa"] = old.pop("whatsapp")
        self.assertEqual(analyze(history=[old])["candidatos"][0]["identidade"], "whatsapp")
        old["cliente_cpf_cnpj"] = "12345678909"
        old["cliente_wa"] = ""
        result = analyze(proposal(documento="123.456.789-09", whatsapp=""), [old])
        self.assertEqual(result["candidatos"][0]["identidade"], "documento")

    def test_nome_exato_sem_identificador_comum_e_indicio_fraco_explicito(self):
        new = proposal(cliente_nome="  CLIENTE  de Teste ", whatsapp="")
        result = analyze(new, [historic(whatsapp="")])
        self.assertEqual(result["candidatos"][0]["identidade"], "nome")
        self.assertIn("indício fraco", result["candidatos"][0]["motivos"][0])

    def test_nome_incompleto_ou_aproximado_nao_tem_fuzzy(self):
        new = proposal(cliente_nome="João Silva", whatsapp="")
        for name in ("João", "Joana Silva", "Joao Silva", "João da Silva"):
            with self.subTest(name=name):
                self.assertFalse(analyze(new, [historic(cliente_nome=name, whatsapp="")])["candidatos"])

    def test_todos_identificadores_e_nome_vazios_nao_encontram_cliente(self):
        new = proposal(cliente_nome="", whatsapp="", documento="", relacionamento_id="")
        old = historic(cliente_nome="", whatsapp="", documento="", relacionamento_id="")
        result = analyze(new, [old])
        self.assertFalse(result["candidatos"])
        self.assertTrue(any("identificação" in warning for warning in result["avisos"]))

    def test_identificador_malformado_nao_se_transforma_em_fallback_por_nome(self):
        for field, value in (("whatsapp", "não informado"), ("documento", "123"), ("whatsapp", "11111111111")):
            with self.subTest(field=field):
                new = proposal(whatsapp="")
                new[field] = value
                self.assertFalse(analyze(new, [historic(whatsapp="")])["candidatos"])

    def test_candidato_nao_expoe_documento_ou_telefone(self):
        old = historic(documento="12345678909")
        result = analyze(proposal(documento="12345678909"), [old])
        serialized = json.dumps(result["candidatos"], ensure_ascii=False)
        self.assertNotIn("12345678909", serialized)
        self.assertNotIn("98765-4321", serialized)
        self.assertNotIn("documento", result["candidatos"][0])
        self.assertNotIn("whatsapp", result["candidatos"][0])


class ItemsAndSourceTest(unittest.TestCase):
    def test_ana_e_bia_nao_sao_personalizacoes_iguais(self):
        self.assertFalse(analyze(history=[historic(itens=[item(nota="Nome: Bia")])])["candidatos"])

    def test_multiconjunto_preserva_linhas_iguais_e_ordem_nao_afeta_match(self):
        lines = [item(nota="Nome: Ana"), item(nota="Nome: Bia"), item(nota="Nome: Ana")]
        result = analyze(proposal(itens=lines), [historic(itens=list(reversed(lines)))])
        self.assertEqual(len(result["candidatos"]), 1)
        self.assertIn("3 linha(s)", result["candidatos"][0]["resumo"])
        self.assertFalse(analyze(proposal(itens=lines), [historic(itens=lines[:2])])["candidatos"])

    def test_duplicadas_iguais_nao_substituem_outra_personalizacao(self):
        new = proposal(itens=[item(nota="Nome: Ana"), item(nota="Nome: Bia")])
        old = historic(itens=[item(nota="Nome: Ana"), item(nota="Nome: Ana")])
        self.assertFalse(analyze(new, [old])["candidatos"])

    def test_quantidade_agregada_nao_equivale_a_duas_linhas(self):
        self.assertFalse(analyze(proposal(itens=[item(quantidade=2)]), [historic(itens=[item(), item()])])["candidatos"])

    def test_quantidades_equivalentes_inteiro_decimal_e_texto(self):
        for quantity in (2, 2.0, "2", "2,0", "2.0", Decimal("2.000")):
            with self.subTest(quantity=quantity):
                self.assertEqual(len(analyze(proposal(itens=[item(quantidade=2)]), [historic(itens=[item(quantidade=quantity)])])["candidatos"]), 1)

    def test_quantidade_invalida_nao_cria_match(self):
        for quantity in (True, False, 0, -1, float("nan"), float("inf"), "", "dois", "2 unidades", "1.000", "2,0,0", {}, None):
            with self.subTest(quantity=repr(quantity)):
                result = analyze(history=[historic(itens=[item(quantidade=quantity)])])
                self.assertFalse(result["candidatos"])
                self.assertEqual(result["itens_incomparaveis"], 1)

    def test_linha_invalida_nao_e_descartada_para_criar_match_parcial(self):
        self.assertFalse(analyze(history=[historic(itens=[item(), None])])["candidatos"])
        self.assertFalse(analyze(proposal(itens=[]), [historic(itens=[])])["candidatos"])

    def test_nome_de_produto_diferente_sem_catalogo_nao_equivale(self):
        self.assertFalse(analyze(history=[historic(itens=[item(nome="Caneca de vidro")])])["candidatos"])

    def test_unidade_de_medida_diferente_nao_equivale(self):
        new = proposal(itens=[item(unidade="caixa")])
        self.assertFalse(analyze(new, [historic(itens=[item(unidade="unidade")])])["candidatos"])

    def test_ids_catalogo_contraditorios_nao_equivalem_mesmo_com_nome_igual(self):
        new = proposal(itens=[item(produto_catalogo_id="CAT-01")])
        old = historic(itens=[item(produto_catalogo_id="CAT-02")])
        self.assertFalse(analyze(new, [old])["candidatos"])

    def test_id_catalogo_igual_admite_renomeacao_e_legado_usa_nome_exato(self):
        new = proposal(itens=[item(produto_catalogo_id="CAT-01")])
        renamed = historic(itens=[item(nome="Nome atualizado", produto_catalogo_id="CAT-01")])
        self.assertEqual(len(analyze(new, [renamed])["candidatos"]), 1)
        self.assertEqual(len(analyze(new, [historic()])["candidatos"]), 1)

    def test_emparelhamento_entre_linhas_com_id_e_legadas_nao_e_guloso(self):
        new = proposal(itens=[item(), item(produto_catalogo_id="CAT-01")])
        old = historic(itens=[item(produto_catalogo_id="CAT-01"), item(produto_catalogo_id="CAT-02")])
        self.assertEqual(len(analyze(new, [old])["candidatos"]), 1)

    def test_emparelhamento_nao_reutiliza_mesma_linha_para_ids_repetidos(self):
        new = proposal(itens=[item(produto_catalogo_id="CAT-01"), item(produto_catalogo_id="CAT-01")])
        old = historic(itens=[item(produto_catalogo_id="CAT-01"), item(produto_catalogo_id="CAT-02")])
        self.assertFalse(analyze(new, [old])["candidatos"])

    def test_preco_unitario_total_e_condicoes_nao_decidem_match(self):
        old = historic(itens=[item(valor_unitario=99.9)], valor_total=99.9, evento="Outra ocasião")
        result = analyze(history=[old])
        self.assertEqual(result["candidatos"][0]["correspondencias"], ["itens"])

    def test_origem_original_exata_encontra_reimportacao_com_itens_ou_preco_alterados(self):
        source = service.SOURCE_PREFIX + "Pedido fictício do site\n1. Caneca\nNome: Ana"
        new = proposal(briefing_origem=source, itens=[item(quantidade=3, valor_unitario=27)])
        old = historic(briefing_origem=source)
        result = analyze(new, [old])
        self.assertEqual(result["candidatos"][0]["correspondencias"], ["origem_site"])

    def test_origem_original_exata_nao_basta_sem_identificar_cliente(self):
        source = service.SOURCE_PREFIX + "Pedido do site"
        new = proposal(cliente_nome="", whatsapp="", briefing_origem=source)
        old = historic(cliente_nome="", whatsapp="", briefing_origem=source)
        self.assertFalse(analyze(new, [old])["candidatos"])

    def test_observacao_generica_prefixo_embutido_e_origem_vazia_nao_sao_mensagem_site(self):
        for source in ("Cliente deseja presente", service.SOURCE_PREFIX, service.SOURCE_PREFIX + " \n ", "Observações\n" + service.SOURCE_PREFIX + "pedido"):
            with self.subTest(source=source):
                new = proposal(briefing_origem=source)
                old = historic(briefing_origem=source, itens=[item(nota="Nome: Bia")])
                self.assertFalse(analyze(new, [old])["candidatos"])

    def test_original_nao_e_truncado_nem_comparado_por_trecho(self):
        source = service.SOURCE_PREFIX + "x" * 20000
        new = proposal(briefing_origem=source + "Ana")
        old = historic(briefing_origem=source + "Bia", itens=[item(nota="Nome: Bia")])
        self.assertFalse(analyze(new, [old])["candidatos"])

    def test_itens_invalidos_ainda_admitem_origem_exata_com_aviso(self):
        source = service.SOURCE_PREFIX + "Pedido fictício do site"
        result = analyze(proposal(briefing_origem=source), [historic(briefing_origem=source, itens=[item(quantidade="inválida")])])
        self.assertEqual(result["candidatos"][0]["correspondencias"], ["origem_site"])
        self.assertTrue(result["avisos"])


class WindowAndStatusTest(unittest.TestCase):
    def test_janela_de_30_datas_inclui_hoje_e_29_dias_anteriores(self):
        dates = [TODAY - timedelta(days=30), TODAY - timedelta(days=29), TODAY, TODAY + timedelta(days=1)]
        history = [historic(numero_proposta=f"P-{i}", data_geracao=when.isoformat()) for i, when in enumerate(dates)]
        result = analyze(history=history)
        self.assertEqual({c["numero"] for c in result["candidatos"]}, {"P-1", "P-2"})
        self.assertEqual(result["data_inicio"], "2026-10-27")
        self.assertEqual(result["data_fim"], "2026-11-25")
        self.assertEqual((result["avaliados"], result["fora_janela"], result["futuros"]), (2, 1, 1))

    def test_data_brasileira_iso_datetime_e_objeto_date(self):
        for when in ("25/11/2026", "2026-11-25", "2026-11-25T10:20:30Z", "25/11/2026 10:20:30", TODAY, datetime(2026, 11, 25, 18)):
            with self.subTest(when=when):
                result = analyze(history=[historic(data_geracao=when)])
                self.assertEqual(result["candidatos"][0]["data"], "25/11/2026")

    def test_sem_data_invalida_e_data_generica_nao_sao_inventadas(self):
        history = [historic(data_geracao=value) for value in (None, "", "31/11/2026", "inválida")]
        history.append({"numero_proposta": "20261125-01", "data": "25/11/2026", **proposal()})
        result = analyze(history=history)
        self.assertEqual(result["sem_data"], 5)
        self.assertFalse(result["candidatos"])
        self.assertTrue(result["avisos"])

    def test_janela_um_dia_somente_hoje(self):
        result = analyze(history=[historic(), historic(data_geracao="24/11/2026")], dias=1)
        self.assertEqual(len(result["candidatos"]), 1)
        self.assertEqual(result["fora_janela"], 1)

    def test_cancelados_entregues_e_legados_participam_com_status_oficial(self):
        history = [
            historic(numero_proposta="CANCELADO", cancelado_cliente=True),
            historic(numero_proposta="ENTREGUE", aprovado=True, entregue=True),
            historic(numero_proposta="LEGADO", Aprovado="sim", Entregue="sim"),
            historic(numero_proposta="ATIVO"),
        ]
        history[2].pop("aprovado")
        candidates = {c["numero"]: c for c in analyze(history=history)["candidatos"]}
        self.assertEqual(len(candidates), 4)
        self.assertEqual(candidates["CANCELADO"]["status"], "Encerrada/cancelada")
        self.assertEqual(candidates["ENTREGUE"]["status"], "Entregue")
        self.assertEqual(candidates["LEGADO"]["status"], "Entregue")
        self.assertEqual(candidates["ATIVO"]["status"], "Aguardando aprovação")

    def test_exclusao_de_numero_somente_quando_explicita(self):
        new = proposal(numero_proposta="PROP-TESTE-01")
        self.assertEqual(len(analyze(new)["candidatos"]), 1)
        result = analyze(new, excluir_numero="PROP-TESTE-01")
        self.assertFalse(result["candidatos"])
        self.assertEqual(result["excluidos"], 1)

    def test_todos_candidatos_retornados_sem_limite_silencioso(self):
        history = [historic(numero_proposta=f"P-{index:03}") for index in range(80)]
        result = analyze(history=history)
        self.assertEqual(len(result["candidatos"]), 80)
        self.assertEqual(result["avaliados"], 80)

    def test_historico_vazio_e_valido_mas_historico_malformado_falha(self):
        self.assertFalse(analyze(history=[])["candidatos"])
        for history in (None, {}, "[]", [None], ["proposta"], [1]):
            with self.subTest(history=history):
                with self.assertRaisesRegex(ValueError, "[Hh]istórico"):
                    service.analisar_duplicidades(proposal(), history, TODAY)

    def test_parametros_invalidos_tem_erro_claro(self):
        for days in (0, -1, 1.5, "30", True, 10 ** 100):
            with self.subTest(days=days):
                with self.assertRaisesRegex(ValueError, "janela"):
                    analyze(dias=days)
        with self.assertRaisesRegex(ValueError, "referência"):
            service.analisar_duplicidades(proposal(), [], "amanhã")
        with self.assertRaisesRegex(ValueError, "proposta"):
            service.analisar_duplicidades(None, [], TODAY)


class FingerprintAndPurityTest(unittest.TestCase):
    def test_assinatura_proposta_cobre_todos_campos_e_contexto_formulario(self):
        new = proposal()
        original = service.assinatura_proposta(new)
        for key, value in (("valor_total", 100), ("data_entrega", "01/12/2026"), ("evento", "Casamento"), ("_contexto_formulario", "form-2"), ("frete_tipo", "Entrega"), ("campo_futuro", "valor novo")):
            with self.subTest(key=key):
                changed = {**new, key: value}
                self.assertNotEqual(original, service.assinatura_proposta(changed))
        changed = deepcopy(new)
        changed["itens"][0]["valor_unitario"] = 99
        self.assertNotEqual(original, service.assinatura_proposta(changed))

    def test_assinatura_estavel_com_ordem_de_chaves_e_numeros_equivalentes(self):
        new = proposal()
        reverse = dict(reversed(list(new.items())))
        reverse["itens"] = [dict(reversed(list(new["itens"][0].items())))]
        reverse["itens"][0]["quantidade"] = Decimal("1.000")
        self.assertEqual(service.assinatura_proposta(new), service.assinatura_proposta(reverse))

    def test_fingerprint_preserva_listas_e_distingue_tipos(self):
        new = proposal(itens=[item(nota="Ana"), item(nota="Bia")])
        changed = {**new, "itens": list(reversed(new["itens"]))}
        self.assertNotEqual(service.assinatura_proposta(new), service.assinatura_proposta(changed))
        self.assertNotEqual(service.assinatura_proposta({"a": True}), service.assinatura_proposta({"a": 1}))
        self.assertNotEqual(service.assinatura_proposta({"a": "1"}), service.assinatura_proposta({"a": 1}))

    def test_assinatura_conferencia_estavel_ao_reordenar_historico_e_candidatos(self):
        new = proposal()
        history = [historic(numero_proposta="P-A"), historic(numero_proposta="P-B")]
        result = analyze(new, history)
        signature = service.assinatura_conferencia(new, result)
        self.assertEqual(signature, service.assinatura_conferencia(new, analyze(new, list(reversed(history)))))
        result["candidatos"].reverse()
        self.assertEqual(signature, service.assinatura_conferencia(new, result))

    def test_preco_payload_alterado_invalida_aceite_com_mesmos_candidatos(self):
        new = proposal()
        result = analyze(new)
        signature = service.assinatura_conferencia(new, result)
        changed = deepcopy(new)
        changed["itens"][0]["valor_unitario"] = 22
        self.assertEqual(result["candidatos"], analyze(changed)["candidatos"])
        self.assertNotEqual(signature, service.assinatura_conferencia(changed, analyze(changed)))

    def test_novo_candidato_e_mudanca_de_status_ou_preco_historico_invalidam_aceite(self):
        new = proposal()
        old = historic()
        signature = service.assinatura_conferencia(new, analyze(new, [old]))
        variants = [
            [old, historic(numero_proposta="P-NOVO")],
            [{**old, "entregue": True}],
            [{**old, "itens": [item(valor_unitario=23)]}],
            [],
        ]
        for history in variants:
            with self.subTest(history=history):
                self.assertNotEqual(signature, service.assinatura_conferencia(new, analyze(new, history)))

    def test_incluir_ou_alterar_registro_alheio_conserva_aceite(self):
        new = proposal()
        old = historic()
        initial = analyze(new, [old])
        signature = service.assinatura_conferencia(new, initial)
        unrelated = historic(numero_proposta="P-ALHEIO", cliente_nome="Outra pessoa", whatsapp="21987654321")
        second = analyze(new, [old, unrelated])
        self.assertNotEqual(initial["avaliados"], second["avaliados"])
        self.assertEqual(signature, service.assinatura_conferencia(new, second))
        unrelated["data_geracao"] = ""
        third = analyze(new, [old, unrelated])
        self.assertNotEqual(second["sem_data"], third["sem_data"])
        self.assertEqual(signature, service.assinatura_conferencia(new, third))

    def test_mudar_janela_ou_dia_invalida_aceite(self):
        new = proposal()
        signature = service.assinatura_conferencia(new, analyze(new))
        self.assertNotEqual(signature, service.assinatura_conferencia(new, analyze(new, dias=31)))
        tomorrow = service.analisar_duplicidades(new, [historic()], TODAY + timedelta(days=1))
        self.assertNotEqual(signature, service.assinatura_conferencia(new, tomorrow))

    def test_mudar_campos_do_candidato_invalida_aceite(self):
        new = proposal()
        result = analyze(new)
        signature = service.assinatura_conferencia(new, result)
        for field, value in (("numero", "P-TROCADO"), ("motivos", ["Outro motivo"]), ("resumo", "Alterado"), ("assinatura", "outra")):
            with self.subTest(field=field):
                changed = deepcopy(result)
                changed["candidatos"][0][field] = value
                self.assertNotEqual(signature, service.assinatura_conferencia(new, changed))

    def test_analise_e_assinaturas_nao_mutam_entradas(self):
        new = proposal()
        history = [historic()]
        before_new, before_history = deepcopy(new), deepcopy(history)
        result = analyze(new, history)
        before_result = deepcopy(result)
        service.assinatura_proposta(new)
        service.assinatura_conferencia(new, result)
        self.assertEqual(new, before_new)
        self.assertEqual(history, before_history)
        self.assertEqual(result, before_result)
        result["candidatos"][0]["motivos"].append("Mudança isolada no resultado")
        self.assertEqual(history, before_history)

    def test_assinatura_rejeita_payload_ou_resultado_nao_serializavel(self):
        for payload in (None, {"x": object()}, {1: "chave inválida"}, {"x": float("nan")}, {"x": float("inf")}):
            with self.subTest(payload=repr(payload)):
                with self.assertRaises(ValueError):
                    service.assinatura_proposta(payload)
        for result in ({}, {"candidatos": None, "janela_dias": 30, "data_inicio": "2026-10-27", "data_fim": "2026-11-25"}):
            with self.assertRaises(ValueError):
                service.assinatura_conferencia(proposal(), result)


if __name__ == "__main__":
    unittest.main()
