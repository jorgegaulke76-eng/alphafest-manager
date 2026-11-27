"""HF57: rascunhos fictícios, parser hostil e retomada sem autoridade operacional."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
import unittest
from unittest.mock import patch

import manager_workflow_hf53 as workflow
import proposal_draft_service_hf57 as service


NOW = datetime(2026, 11, 25, 14, 30, 15, 123456, tzinfo=timezone(timedelta(hours=-3)))
VERSION = "20.4.9-HF65.24.57"


def item(**changes):
    return {"produto": "Caneca personalizada", "especificacoes": " Nome: Ana\nCor: azul ",
            "quantidade": 1.5, "valor_unitario": 18.5,
            "produto_catalogo_id": "CAT-TESTE-1", "produto_origem": "catalogo_alias",
            "preco_especial_aplicado": True, "valor_base_oficial": 20,
            "metadata": {"arte": "arte-ana.pdf", "cores": ["azul", "prata"],
                         "zero": 0, "flag": False, "nulo": None, "vazio": ""}, **changes}


def state(*, anna=False):
    prefix = "anna_modal_" if anna else "form_"
    values = dict(cliente=" Cliente de teste ", documento="", whatsapp="11999999999", evento="Festa",
                  observacoes="Mensagem recebida do site:\n1. Caneca\nPersonalização/observações: Nome: Ana\n",
                  desconto=2.0, taxa_entrega=8.0, entrega=date(2026, 11, 30),
                  prazo="a combinar", frete="Entrega", validade="")
    result = {prefix + key: value for key, value in values.items()}
    result.update({"anna_modal_itens" if anna else "temp_itens": [item()],
                   "anna_modal_item_key" if anna else "form_key": 3,
                   "anna_modal_numero_original" if anna else "editar_numero": "PROP-TESTE-1"})
    origin_prefix = "_anna_hf53" if anna else ""
    result[origin_prefix + "_atendimento_origem_id"] = "AT-TESTE-1"
    result[origin_prefix + "_projeto_origem_id"] = "PR-TESTE-1"
    return result


def capture(source=None, *, anna=False, now=NOW, version=VERSION):
    return service.capturar_rascunho(state(anna=anna) if source is None else source,
                                    anna=anna, agora=now, versao_manager=version)


def with_pending(source, *, anna=False, editor=True):
    result = deepcopy(source)
    sequence = result["anna_modal_item_key" if anna else "form_key"]
    prefix = "anna_modal_" if anna else ""
    product = f"anna_modal_prod_{sequence}" if anna else f"produto_novo_{sequence}"
    result.update({product + "_catalogo": "Produto livre / novo", product + "_livre": "  Topo de bolo  ",
                   f"{prefix}qtd_{sequence}": 2.5, f"{prefix}valor_{sequence}": 12.0,
                   f"{prefix}tema_{sequence}": " Tema espaço ",
                   f"{prefix}nome_item_{sequence}": "Ana e Bia\n",
                   f"{prefix}cor_{sequence}": "azul", f"{prefix}idade_{sequence}": "8",
                   f"{prefix}{'obs' if anna else 'obs_item'}_{sequence}": "  Não aparar  "})
    if editor:
        profile = "anna" if anna else "jorge"
        result["_hf53_edicao_" + profile] = {"indice": 0, "original": deepcopy(result["anna_modal_itens" if anna else "temp_itens"][0]), "token": 7}
        editor_prefix = f"hf53_item_{profile}_7"
        result.update({editor_prefix + "_produto": "Caneca revisada", editor_prefix + "_especificacoes": "Nome: Bia\n",
                       editor_prefix + "_quantidade": 3.5, editor_prefix + "_valor": 19.0})
    return result


def encoded(document):
    return json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


class CaptureAndRoundtripTest(unittest.TestCase):
    def test_captura_roundtrip_preserva_dados_e_metadata_integrais(self):
        source = state()
        before = deepcopy(source)
        document = capture(source)
        raw = service.exportar_rascunho(document)
        self.assertIsInstance(raw, bytes)
        imported = service.importar_rascunho(raw)
        self.assertEqual(imported, document)
        self.assertEqual(document["formulario"]["itens"], before["temp_itens"])
        self.assertEqual(document["formulario"]["observacoes"], before["form_observacoes"])
        self.assertEqual(document["formulario"]["entrega"], "2026-11-30")
        self.assertEqual(document["criado_em"], NOW.isoformat())
        self.assertEqual(document["origem"], {"perfil": "jorge", "numero_proposta": "PROP-TESTE-1",
                                            "atendimento_id": "AT-TESTE-1", "projeto_id": "PR-TESTE-1"})
        self.assertEqual(source, before)
        self.assertEqual(service.importar_rascunho(raw.decode("utf-8")), imported)

    def test_rascunho_parcial_sem_cliente_itens_ou_data_e_valido(self):
        document = capture({})
        self.assertEqual(document["formulario"]["cliente"], "")
        self.assertEqual(document["formulario"]["itens"], [])
        self.assertIsNone(document["formulario"]["entrega"])
        self.assertEqual(document["pendencias"], {"item_nao_adicionado": [], "edicao_item": []})
        self.assertEqual(service.importar_rascunho(service.exportar_rascunho(document)), document)
        self.assertIsNone(service.preparar_retomada(document)["entrega"])

    def test_default_legado_jorge_sem_itens_exporta_modalidade_do_seletor(self):
        source = {"form_frete": "Retirada em Itatiba", "temp_itens": []}
        document = capture(source)
        self.assertEqual(document["formulario"]["frete"], "Retirada")
        self.assertEqual(source["form_frete"], "Retirada em Itatiba")
        self.assertEqual(service.preparar_retomada(document)["frete"], "Retirada")
        document["formulario"]["frete"] = "Retirada em Itatiba"
        with self.assertRaisesRegex(ValueError, "frete"):
            service.importar_rascunho(encoded(document))

    def test_quantidades_fracionarias_zero_e_negativos_sao_preservados_para_conferencia(self):
        source = state()
        source["temp_itens"] = [item(quantidade=1.25), item(quantidade=0, valor_unitario=0, produto=""),
                                item(quantidade=-2.5, valor_unitario=-19)]
        document = service.importar_rascunho(service.exportar_rascunho(capture(source)))
        self.assertEqual(document["formulario"]["itens"], source["temp_itens"])

    def test_captura_apenas_whitelist_sem_aceites_status_cache_ou_segredos(self):
        source = state()
        source.update({"numero_proposta": "INJETADO", "aprovado": True, "pago": True,
                       "_hf55_jorge_conferencia_duplicidades": {"confirmada": True},
                       "_hf56_jorge_revisao_final": {"confirmada": True},
                       "_document_cache": {"segredo": "nao_exportar"}, "token_sessao": "nao_exportar"})
        document = capture(source)
        text = service.exportar_rascunho(document).decode("utf-8")
        for forbidden in ("INJETADO", "nao_exportar", "confirmada", "_document_cache", "token_sessao"):
            self.assertNotIn(forbidden, text)
        self.assertEqual(set(document["formulario"]), set(workflow.QUOTE_FIELDS) | {"itens"})

    def test_metadata_com_id_status_e_nomes_de_campos_nao_e_removido_recursivamente(self):
        source = state()
        source["temp_itens"][0]["metadata"] = {"id": "ARTE-1", "status": "revisado",
                                                  "manager_version": "versão da arte", "criado_em": "texto da arte"}
        result = service.preparar_retomada(service.importar_rascunho(service.exportar_rascunho(capture(source))))
        self.assertEqual(result["itens"], source["temp_itens"])
        self.assertNotIn("status", result)

    def test_perfis_usam_somente_os_proprios_widgets_e_itens(self):
        source = state()
        source.update(state(anna=True))
        source["anna_modal_cliente"] = "Cliente Anna"
        source["anna_modal_itens"] = [item(especificacoes="Nome Bia")]
        jorge, anna = capture(source), capture(source, anna=True)
        self.assertEqual(jorge["formulario"]["cliente"], " Cliente de teste ")
        self.assertEqual(anna["formulario"]["cliente"], "Cliente Anna")
        self.assertEqual(anna["origem"]["perfil"], "anna")
        self.assertEqual(anna["formulario"]["itens"][0]["especificacoes"], "Nome Bia")

    def test_documento_capturado_nao_compartilha_referencias_mutaveis_com_estado(self):
        source = state()
        document = capture(source)
        source["temp_itens"][0]["metadata"]["cores"].append("rosa")
        self.assertNotIn("rosa", document["formulario"]["itens"][0]["metadata"]["cores"])
        document["formulario"]["itens"][0]["metadata"]["cores"].append("verde")
        self.assertNotIn("verde", source["temp_itens"][0]["metadata"]["cores"])

    def test_exportacao_invalida_nao_altera_estado(self):
        source = state()
        source["form_desconto"] = -1
        before = deepcopy(source)
        with self.assertRaisesRegex(ValueError, "desconto"):
            capture(source)
        self.assertEqual(source, before)

    def test_captura_data_date_datetime_iso_ou_nula(self):
        for delivery, expected in ((date(2026, 11, 30), "2026-11-30"),
                                   (datetime(2026, 11, 30, 10), "2026-11-30"),
                                   ("2026-11-30", "2026-11-30"), (None, None)):
            with self.subTest(delivery=delivery):
                source = state()
                source["form_entrega"] = delivery
                self.assertEqual(capture(source)["formulario"]["entrega"], expected)


class PendingRecoveryTest(unittest.TestCase):
    def test_item_nao_adicionado_preserva_texto_confirmado_sem_aplicar(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                source = with_pending(state(anna=anna), anna=anna, editor=False)
                before = deepcopy(source)
                document = capture(source, anna=anna)
                pending = document["pendencias"]["item_nao_adicionado"]
                self.assertEqual(len(pending), 1)
                self.assertEqual(pending[0]["produto_livre"], "  Topo de bolo  ")
                self.assertEqual(pending[0]["detalhes"]["tema"], " Tema espaço ")
                self.assertEqual(pending[0]["detalhes"]["obs" if anna else "obs_item"], "  Não aparar  ")
                self.assertEqual(pending[0]["quantidade"], 2.5)
                prepared = service.preparar_retomada(document)
                self.assertEqual(len(prepared["itens"]), 1)
                self.assertEqual(prepared["_hf57_pendencias"], document["pendencias"])
                self.assertEqual(source, before)

    def test_geracoes_antigas_nao_viram_pendencias_atuais(self):
        source = state()
        source.update({"produto_novo_2_livre": "Item antigo", "tema_2": "Tema antigo", "valor_2": 999})
        self.assertEqual(capture(source)["pendencias"]["item_nao_adicionado"], [])

    def test_edicao_preserva_original_e_widgets_confirmados_sem_token_ativo(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                source = with_pending(state(anna=anna), anna=anna)
                document = capture(source, anna=anna)
                editor = document["pendencias"]["edicao_item"][0]
                self.assertEqual(set(editor), {"indice", "original", "campos"})
                self.assertEqual(editor["original"], source["anna_modal_itens" if anna else "temp_itens"][0])
                self.assertEqual(editor["campos"], {"produto": "Caneca revisada", "especificacoes": "Nome: Bia\n",
                                                    "quantidade": 3.5, "valor_unitario": 19.0})
                self.assertEqual(service.preparar_retomada(document)["itens"][0]["produto"], "Caneca personalizada")

    def test_editor_sem_widgets_confirmados_guarda_somente_valores_originais(self):
        source = state()
        source["_hf53_edicao_jorge"] = {"indice": 0, "original": deepcopy(source["temp_itens"][0]), "token": 9}
        result = capture(source)["pendencias"]["edicao_item"][0]
        self.assertEqual(result["campos"], {key: source["temp_itens"][0][key]
                                             for key in ("produto", "especificacoes", "quantidade", "valor_unitario")})

    def test_reexportacao_combina_referencias_recuperadas_e_pendencias_novas(self):
        original = capture(with_pending(state()))
        prepared = service.preparar_retomada(original)
        source = with_pending(state(anna=True), anna=True)
        source["anna_modal_numero_original"] = ""
        source["_anna_hf53_atendimento_origem_id"] = ""
        source["_anna_hf53_projeto_origem_id"] = ""
        source["_hf57_origem_rascunho_anna"] = prepared["_hf57_origem"]
        source["_hf57_pendencias_rascunho_anna"] = prepared["_hf57_pendencias"]
        source["hf53_item_anna_7_especificacoes"] = "Nome: Carla"
        new = capture(source, anna=True)
        self.assertEqual(new["origem"], original["origem"])
        self.assertEqual(len(new["pendencias"]["item_nao_adicionado"]), 2)
        self.assertEqual(len(new["pendencias"]["edicao_item"]), 2)
        self.assertEqual(new["pendencias"]["edicao_item"][0], original["pendencias"]["edicao_item"][0])
        self.assertEqual(service.importar_rascunho(service.exportar_rascunho(new)), new)

    def test_reexportacao_deduplica_so_referencias_integralmente_iguais(self):
        source = with_pending(state())
        recovered = capture(source)["pendencias"]
        source["_hf57_pendencias_rascunho_jorge"] = deepcopy(recovered)
        self.assertEqual(capture(source)["pendencias"], recovered)
        source["hf53_item_jorge_7_valor"] = 20.0
        result = capture(source)["pendencias"]
        self.assertEqual(len(result["edicao_item"]), 2)
        self.assertEqual(len(result["item_nao_adicionado"]), 1)

    def test_limite_de_50_pendencias_recusa_51_sem_truncar(self):
        source = with_pending(state(), editor=False)
        reference = capture(source)["pendencias"]["item_nao_adicionado"][0]
        references = [dict(deepcopy(reference), sequencia=index + 10) for index in range(service.MAX_PENDING)]
        source["_hf57_pendencias_rascunho_jorge"] = {"item_nao_adicionado": references, "edicao_item": []}
        before = deepcopy(source)
        with self.assertRaisesRegex(ValueError, "50"):
            capture(source)
        self.assertEqual(source, before)
        source["_hf57_pendencias_rascunho_jorge"]["item_nao_adicionado"][-1] = reference
        self.assertEqual(len(capture(source)["pendencias"]["item_nao_adicionado"]), 50)

    def test_pendencia_hostil_nao_pode_incluir_widget_status_ou_campo_extra(self):
        document = capture(with_pending(state()))
        for kind, field in (("item_nao_adicionado", "aprovado"), ("edicao_item", "token")):
            with self.subTest(kind=kind):
                bad = deepcopy(document)
                bad["pendencias"][kind][0][field] = True
                with self.assertRaises(ValueError):
                    service.importar_rascunho(encoded(bad))


class NewQuoteAndSignatureTest(unittest.TestCase):
    def test_retomada_nunca_herda_ids_ativos_status_ou_confirmacoes(self):
        document = capture(with_pending(state()))
        before = deepcopy(document)
        data = service.preparar_retomada(document)
        self.assertEqual(set(data), set(workflow.QUOTE_FIELDS) | {"itens", "_hf57_retomada", "_hf57_origem", "_hf57_pendencias"})
        for name in ("numero_proposta", "editar_numero", "atendimento_id", "projeto_id", "aprovado", "pago", "pronto", "entregue", "confirmada"):
            self.assertNotIn(name, data)
        self.assertEqual(data["_hf57_origem"]["numero_proposta"], "PROP-TESTE-1")
        self.assertEqual(data["entrega"], date(2026, 11, 30))
        self.assertEqual(document, before)
        data["itens"][0]["metadata"]["cores"].clear()
        self.assertEqual(document, before)

    def test_workflow_real_abre_como_novo_em_ambos_os_perfis_sem_reativar_vinculos(self):
        for anna in (False, True):
            with self.subTest(anna=anna):
                prepared = service.preparar_retomada(capture(with_pending(state(anna=not anna), anna=not anna)))
                target = {}
                workflow.solicitar_abertura(target, "novo_orcamento", prepared, anna=anna)
                result = workflow.resolver_abertura(target, "abrir", hoje=NOW.date())
                self.assertTrue(result["aplicado"])
                self.assertEqual(target["anna_modal_itens" if anna else "temp_itens"], prepared["itens"])
                self.assertFalse(target["anna_modal_numero_original" if anna else "editar_numero"])
                origin_prefix = "_anna_hf53" if anna else ""
                self.assertEqual(target[origin_prefix + "_atendimento_origem_id"], "")
                self.assertEqual(target[origin_prefix + "_projeto_origem_id"], "")
                self.assertNotIn("_hf53_edicao_anna" if anna else "_hf53_edicao_jorge", target)

    def test_origem_ativa_nova_prevalece_sem_misturar_ids_anteriores(self):
        old = service.preparar_retomada(capture())
        source = state(anna=True)
        source["anna_modal_numero_original"] = "PROP-ATUAL-2"
        source["_anna_hf53_atendimento_origem_id"] = ""
        source["_anna_hf53_projeto_origem_id"] = ""
        source["_hf57_origem_rascunho_anna"] = old["_hf57_origem"]
        self.assertEqual(capture(source, anna=True)["origem"], {"perfil": "anna", "numero_proposta": "PROP-ATUAL-2",
                                                               "atendimento_id": "", "projeto_id": ""})

    def test_assinatura_ignora_somente_metadados_temporais_do_envelope(self):
        document = capture()
        expected = service.assinatura_rascunho(document)
        changed = deepcopy(document)
        changed.update(criado_em="2030-01-01T10:00:00+00:00", manager_version="versão seguinte")
        self.assertEqual(expected, service.assinatura_rascunho(changed))
        for field in ("criado_em", "manager_version"):
            changed = deepcopy(document)
            changed["formulario"]["itens"][0]["metadata"][field] = "dado da arte"
            self.assertNotEqual(expected, service.assinatura_rascunho(changed))

    def test_assinatura_estavel_independente_da_ordem_de_chaves(self):
        def reverse(value):
            if isinstance(value, dict):
                return {key: reverse(child) for key, child in reversed(list(value.items()))}
            if isinstance(value, list):
                return [reverse(child) for child in value]
            return value
        document = capture(with_pending(state()))
        self.assertEqual(service.assinatura_rascunho(document), service.assinatura_rascunho(reverse(document)))

    def test_assinatura_muda_com_conteudo_origem_pendencias_ou_ordem_de_itens(self):
        document = capture(with_pending(state()))
        expected = service.assinatura_rascunho(document)
        modifications = [lambda value: value["formulario"].update(cliente="Outro cliente"),
                         lambda value: value["origem"].update(numero_proposta="P-2"),
                         lambda value: value["formulario"]["itens"][0].update(valor_unitario=20),
                         lambda value: value["pendencias"]["edicao_item"][0]["campos"].update(especificacoes="Nova nota")]
        for modify in modifications:
            changed = deepcopy(document)
            modify(changed)
            self.assertNotEqual(expected, service.assinatura_rascunho(changed))
        document["formulario"]["itens"].append(item(especificacoes="Nome Bia"))
        first = service.assinatura_rascunho(document)
        document["formulario"]["itens"].reverse()
        self.assertNotEqual(first, service.assinatura_rascunho(document))

    def test_apis_nao_abrem_arquivos_rede_ou_executam_texto_importado(self):
        source = state()
        source["form_observacoes"] = "__import__('os').system('nao executar')"
        with patch("builtins.open", side_effect=AssertionError("Arquivo não autorizado")), \
             patch("socket.socket", side_effect=AssertionError("Rede não autorizada")), \
             patch("builtins.eval", side_effect=AssertionError("Execução não autorizada")):
            document = capture(source)
            imported = service.importar_rascunho(service.exportar_rascunho(document))
            service.assinatura_rascunho(imported)
            self.assertEqual(service.preparar_retomada(imported)["observacoes"], source["form_observacoes"])


class StructuralValidationTest(unittest.TestCase):
    def test_schema_campos_e_versao_exigem_contrato_exato(self):
        valid = capture()
        for key, value in (("schema", "outro"), ("schema_version", 2), ("schema_version", 1.0),
                           ("schema_version", True), ("manager_version", None), ("aprovado", True)):
            with self.subTest(key=key, value=value):
                bad = deepcopy(valid)
                bad[key] = value
                with self.assertRaises(ValueError):
                    service.importar_rascunho(encoded(bad))
        for key in valid:
            bad = deepcopy(valid)
            del bad[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                service.importar_rascunho(encoded(bad))

    def test_status_comandos_e_ids_ativos_extras_nao_entram_no_formulario(self):
        for target in ("formulario", "origem", "pendencias"):
            bad = capture()
            bad[target]["editar_numero"] = "P-INJETADO"
            with self.subTest(target=target), self.assertRaises(ValueError):
                service.importar_rascunho(encoded(bad))

    def test_campos_textuais_precisam_ser_strings_sem_coercao(self):
        for field in ("cliente", "documento", "whatsapp", "evento", "observacoes", "prazo", "validade"):
            for value in (None, True, 10, [], {}):
                bad = capture()
                bad["formulario"][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    service.exportar_rascunho(bad)

    def test_desconto_taxa_e_frete_compativeis_com_widgets(self):
        for field in ("desconto", "taxa_entrega"):
            for value in (-1, True, "2,50", None, float("nan"), float("inf"), 10 ** 400):
                bad = capture()
                bad["formulario"][field] = value
                with self.subTest(field=field, value=repr(value)), self.assertRaises(ValueError):
                    service.exportar_rascunho(bad)
        for value in ("Correios", "retirada", "Entrega ", None, []):
            bad = capture()
            bad["formulario"]["frete"] = value
            with self.subTest(frete=value), self.assertRaises(ValueError):
                service.exportar_rascunho(bad)

    def test_inteiros_comerciais_nao_podem_perder_precisao_no_widget_float(self):
        for field in ("desconto", "taxa_entrega", "quantidade", "valor_unitario"):
            document = capture(with_pending(state()))
            target = document["formulario"] if field in ("desconto", "taxa_entrega") else document["formulario"]["itens"][0]
            target[field] = 2 ** 53 + 1
            before = deepcopy(document)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "representado exatamente"):
                service.importar_rascunho(encoded(document))
            self.assertEqual(document, before)
            for exact in (0, 12, 2 ** 53, 2 ** 53 + 2, 2 ** 60):
                target[field] = exact
                self.assertEqual(service.importar_rascunho(service.exportar_rascunho(document)), document)
        for kind in ("item_nao_adicionado", "edicao_item"):
            document = capture(with_pending(state()))
            target = document["pendencias"][kind][0]
            if kind == "edicao_item":
                target = target["campos"]
            target["quantidade"] = -(2 ** 53 + 1)
            with self.subTest(pending=kind), self.assertRaisesRegex(ValueError, "representado exatamente"):
                service.exportar_rascunho(document)

    def test_precisao_de_inteiros_em_metadata_desconhecida_e_preservada(self):
        document = capture()
        document["formulario"]["itens"][0]["metadata"] = {
            "id_legado": 2 ** 53 + 1, "referencia_grande": 2 ** 128 + 1,
            "quantidade": 2 ** 53 + 1,
        }
        imported = service.importar_rascunho(service.exportar_rascunho(document))
        self.assertEqual(imported, document)
        self.assertEqual(service.preparar_retomada(imported)["itens"][0]["metadata"], document["formulario"]["itens"][0]["metadata"])

    def test_itens_recusam_formatos_e_numeros_incompativeis(self):
        for value in (None, {}, "itens", [None], [1], [[]], [{}]):
            bad = capture()
            bad["formulario"]["itens"] = value
            with self.subTest(items=value), self.assertRaises(ValueError):
                service.exportar_rascunho(bad)
        for field, values in (("produto", (None, 3)), ("especificacoes", (None, [])),
                              ("quantidade", (None, True, "1,5", float("inf"))),
                              ("valor_unitario", (None, True, "18.5", float("nan")))):
            for value in values:
                bad = capture()
                bad["formulario"]["itens"][0][field] = value
                with self.subTest(field=field, value=repr(value)), self.assertRaises(ValueError):
                    service.exportar_rascunho(bad)

    def test_metadata_inteiro_enorme_nao_finito_ou_tipo_nao_json_e_recusado(self):
        for value in (float("nan"), float("inf"), -float("inf"), 10 ** 400, b"arquivo", Decimal("1.5"),
                      {"conjunto"}, (1, 2), NOW, object(), {1: "chave não textual"}):
            bad = capture()
            bad["formulario"]["itens"][0]["metadata"] = {"conteudo": value}
            with self.subTest(value=type(value).__name__), self.assertRaises(ValueError):
                service.exportar_rascunho(bad)

    def test_datas_impossiveis_formatos_e_fuso_ausente_sao_recusados(self):
        for value in ("30/11/2026", "2026-02-29", "2026-11-31", "2026-11-30T10:00:00", "", 20261130):
            bad = capture()
            bad["formulario"]["entrega"] = value
            with self.subTest(delivery=value), self.assertRaises(ValueError):
                service.exportar_rascunho(bad)
        for now in (NOW.replace(tzinfo=None), "2026-11-25T10:00:00", "2026-02-29T10:00:00+00:00", "hoje", None):
            with self.subTest(now=now), self.assertRaises(ValueError):
                capture(now=now)
        self.assertEqual(capture(now="2026-11-25T10:00:00Z")["criado_em"], "2026-11-25T10:00:00Z")

    def test_datas_extremas_nao_podem_derrubar_date_input_na_retomada(self):
        for value in ("0001-01-01", "0010-12-31", "0011-01-01", "1009-12-31", "9990-01-01", "9999-12-31"):
            bad = capture()
            bad["formulario"]["entrega"] = value
            with self.subTest(delivery=value), self.assertRaisesRegex(ValueError, "formulário"):
                service.importar_rascunho(encoded(bad))
        for value in ("1010-01-01", "1900-01-01", "9989-12-31"):
            good = capture()
            good["formulario"]["entrega"] = value
            self.assertEqual(service.preparar_retomada(good)["entrega"], date.fromisoformat(value))


class ParserAndLimitsTest(unittest.TestCase):
    def test_chaves_duplicadas_inclusive_unicode_escape_e_metadata_sao_recusadas(self):
        raw = service.exportar_rascunho(capture()).decode("utf-8")
        variants = [raw.replace('"schema":', '"schema":"outro","schema":', 1),
                    raw.replace('"cliente":', '"cliente":"outro","cliente":', 1),
                    raw.replace('"zero":0', '"nome":0,"\\u006eome":1', 1)]
        for text in variants:
            with self.subTest(text=text[:50]), self.assertRaisesRegex(ValueError, "duplicada"):
                service.importar_rascunho(text)

    def test_nan_infinity_e_overflow_exponencial_no_json_sao_recusados(self):
        raw = service.exportar_rascunho(capture()).decode("utf-8")
        for token in ("NaN", "Infinity", "-Infinity", "1e309", "-1e309"):
            with self.subTest(token=token), self.assertRaisesRegex(ValueError, "finit"):
                service.importar_rascunho(raw.replace('"zero":0', '"zero":' + token, 1))

    def test_json_malformado_raiz_invalida_ou_tipo_de_entrada_incompativel(self):
        for raw in ("", " ", "{}{}", "{", '{"x":1,}', "//comentário\n{}", "null", "[]", '"texto"', "1", b"\xef\xbb\xbf{}", {}, bytearray(b"{}")):
            with self.subTest(raw=repr(raw)), self.assertRaises(ValueError):
                service.importar_rascunho(raw)

    def test_utf8_invalido_utf16_e_surrogate_escapado_nao_entram(self):
        for raw in (b"\xff", b"\xc3(", "{}".encode("utf-16"), "{}".encode("utf-32"), "\ud800"):
            with self.subTest(raw=repr(raw)), self.assertRaises(ValueError):
                service.importar_rascunho(raw)
        bad = capture()
        bad["formulario"]["observacoes"] = "\ud800"
        with self.assertRaisesRegex(ValueError, "Unicode"):
            service.importar_rascunho(json.dumps(bad, ensure_ascii=True))
        with self.assertRaisesRegex(ValueError, "Unicode"):
            service.exportar_rascunho(bad)

    def test_json_extremamente_profundo_e_inteiro_com_muitos_digitos_tem_erro_legivel(self):
        for raw in ("[" * 2000 + "0" + "]" * 2000, "9" * 5000):
            with self.subTest(kind=raw[0]), self.assertRaisesRegex(ValueError, "Rascunho inválido"):
                service.importar_rascunho(raw)

    def test_limite_exato_de_2mib_e_um_byte_a_mais(self):
        raw = service.exportar_rascunho(capture())
        exact = raw + b" " * (service.MAX_BYTES - len(raw))
        self.assertEqual(service.importar_rascunho(exact), capture())
        with self.assertRaisesRegex(ValueError, "2 MiB"):
            service.importar_rascunho(exact + b" ")

    def test_limite_e_em_bytes_utf8_e_exportacao_nao_trunca(self):
        bad = capture()
        bad["formulario"]["itens"][0]["metadata"] = {str(index): "🎈" * service.MAX_TEXT for index in range(6)}
        raw = json.dumps(bad, ensure_ascii=False)
        self.assertLess(len(raw), service.MAX_BYTES)
        self.assertGreater(len(raw.encode("utf-8")), service.MAX_BYTES)
        before = deepcopy(bad)
        with self.assertRaisesRegex(ValueError, "2 MiB"):
            service.importar_rascunho(raw)
        with self.assertRaisesRegex(ValueError, "2 MiB"):
            service.exportar_rascunho(bad)
        self.assertEqual(bad, before)

    def test_limite_de_texto_inclusive_chaves_e_metadados(self):
        document = capture()
        document["formulario"]["observacoes"] = "x" * service.MAX_TEXT
        self.assertEqual(service.importar_rascunho(service.exportar_rascunho(document)), document)
        for target in ("campo", "metadata", "chave"):
            bad = capture()
            long = "x" * (service.MAX_TEXT + 1)
            if target == "campo":
                bad["formulario"]["observacoes"] = long
            elif target == "metadata":
                bad["formulario"]["itens"][0]["metadata"]["extra"] = long
            else:
                bad["formulario"]["itens"][0]["metadata"][long] = 1
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "caracteres"):
                service.exportar_rascunho(bad)

    def test_profundidade_12_e_13_na_metadata(self):
        def chain(levels):
            result = 0
            for _ in range(levels):
                result = [result]
            return result
        document = capture()
        document["formulario"]["itens"][0]["metadata"] = chain(7)
        self.assertEqual(service.importar_rascunho(service.exportar_rascunho(document)), document)
        document["formulario"]["itens"][0]["metadata"] = chain(8)
        with self.assertRaisesRegex(ValueError, "profundidade"):
            service.exportar_rascunho(document)

    def test_limite_de_40mil_nos_inclui_toda_metadata(self):
        def count(value):
            if isinstance(value, dict):
                return 1 + sum(count(child) for child in value.values())
            if isinstance(value, list):
                return 1 + sum(count(child) for child in value)
            return 1
        document = capture()
        document["formulario"]["itens"][0]["metadata"] = []
        document["formulario"]["itens"][0]["metadata"] = [0] * (service.MAX_NODES - count(document))
        self.assertEqual(count(document), service.MAX_NODES)
        self.assertEqual(service.importar_rascunho(service.exportar_rascunho(document)), document)
        document["formulario"]["itens"][0]["metadata"].append(0)
        with self.assertRaisesRegex(ValueError, "nós"):
            service.exportar_rascunho(document)

    def test_mil_itens_sao_preservados_e_mil_e_um_recusados(self):
        document = capture()
        simple = {"produto": "Caneca", "especificacoes": "Nome Ana", "quantidade": 1, "valor_unitario": 1}
        document["formulario"]["itens"] = [dict(simple) for _ in range(service.MAX_ITEMS)]
        self.assertEqual(len(service.importar_rascunho(service.exportar_rascunho(document))["formulario"]["itens"]), 1000)
        document["formulario"]["itens"].append(dict(simple))
        with self.assertRaisesRegex(ValueError, "1.000 itens"):
            service.exportar_rascunho(document)

    def test_referencia_circular_e_rejeitada_sem_recursionerror(self):
        document = capture()
        document["formulario"]["itens"][0]["metadata"]["ciclo"] = document
        with self.assertRaisesRegex(ValueError, "circular"):
            service.exportar_rascunho(document)


if __name__ == "__main__":
    unittest.main()
