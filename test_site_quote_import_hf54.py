"""Importador HF54: serviço puro, mensagem real do gerador e dados fictícios."""
from copy import deepcopy
from decimal import Decimal
import json
import re
import subprocess
import unittest

import site_carrinho_orcamento_service as cart
import site_quote_import_service as service


CATALOG = [
    {"Nome": "Caneca Personalizada", "Aliases": ["Caneca", "CANEQUINHA"], "CatalogoId": "CAT-01", "Preco": "R$ 18,50", "Ativo": True},
    {"Nome": "Topo de Bolo", "Aliases": "Topo; Topper", "CatalogoId": "CAT-02", "Preco": 12.0},
]


def site_message(items):
    """Executa a função message() emitida pelo serviço de produção, sem DOM/rede."""
    function = re.search(r"^  function message\(\)\{[^\n]+\}", cart.JS, re.M)
    if not function:
        raise AssertionError("A função message() do site mudou: revisar o contrato da importação.")
    program = "const items=" + json.dumps(items, ensure_ascii=False) + ";\n" + function[0] + "\nprocess.stdout.write(message());"
    result = subprocess.run(["node", "-"], input=program, text=True, capture_output=True, check=True, timeout=10)
    return result.stdout


def message(name="Caneca", quantity=2, note="Tema: Espaço\nNome: Lia | Cor: azul"):
    return site_message([{"name": name, "quantity": quantity, "note": note}])


class SiteQuoteImportTest(unittest.TestCase):
    def test_mensagem_emitida_pelo_site_preserva_detalhes_e_sugere_preco_catalogo(self):
        source = message()
        analysis = service.analisar_mensagem(source, CATALOG)
        self.assertFalse(analysis["erros"])
        self.assertEqual(analysis["texto_original"], source)
        item = analysis["itens"][0]
        self.assertEqual(item["produto"], "Caneca Personalizada")
        self.assertEqual(item["produto_recebido"], "Caneca")
        self.assertEqual(item["status_catalogo"], "alias")
        self.assertEqual(item["produto_origem"], "catalogo_alias")
        self.assertEqual(item["produto_catalogo_id"], "CAT-01")
        self.assertEqual(item["quantidade"], 2)
        self.assertEqual(item["valor_unitario"], 18.5)
        self.assertEqual(item["especificacoes"], "Tema: Espaço\nNome: Lia | Cor: azul")

    def test_orcamento_longo_de_25_itens_nao_corta_mensagem_nem_ultimo_item(self):
        source = site_message([{"name": f"Produto {i:02}", "quantity": i, "note": "Nome: " + str(i) + " • " + "x"*450} for i in range(1, 26)])
        self.assertGreater(len(source), 12000)
        analysis = service.analisar_mensagem(source, [])
        self.assertEqual(len(analysis["itens"]), 25)
        draft = service.preparar_rascunho(analysis, deepcopy(analysis["itens"]), confirmar_sem_preco=True)
        self.assertEqual(draft["observacoes"], service.SOURCE_PREFIX + source)
        self.assertEqual(draft["itens"][-1]["produto"], "Produto 25")
        self.assertEqual(draft["itens"][-1]["especificacoes"], "Nome: 25 • " + "x"*450)

    def test_produto_repetido_com_personalizacoes_distintas_nao_e_mesclado(self):
        source = site_message([{"name": "Caneca", "quantity": 1, "note": "Nome: Ana"}, {"name": "Caneca", "quantity": 1, "note": "Nome: Bia"}])
        analysis = service.analisar_mensagem(source, CATALOG)
        draft = service.preparar_rascunho(analysis, deepcopy(analysis["itens"]))
        self.assertEqual(len(draft["itens"]), 2)
        self.assertEqual([x["especificacoes"] for x in draft["itens"]], ["Nome: Ana", "Nome: Bia"])
        self.assertEqual([x["produto_catalogo_id"] for x in draft["itens"]], ["CAT-01", "CAT-01"])

    def test_nota_multilinha_com_enumeracao_e_linhas_em_branco_permanece_nota(self):
        note = "Nomes:\n1. Ana\n2. Bia\n\nCores:\n1. Azul\n2. Rosa"
        analysis = service.analisar_mensagem(message(note=note), CATALOG)
        self.assertFalse(analysis["erros"])
        self.assertEqual(len(analysis["itens"]), 1)
        self.assertEqual(analysis["itens"][0]["especificacoes"], note)
        self.assertTrue(any("lista numerada" in a for a in analysis["itens"][0]["avisos"]))

    def test_quantidade_com_virgula_e_separador_de_milhar(self):
        for raw, expected in (("1,5", 1.5), ("1.234,5", 1234.5), ("25", 25), ("0.5", 0.5)):
            with self.subTest(raw=raw):
                analysis = service.analisar_mensagem(f"1. Caneca\nQuantidade: {raw}", CATALOG)
                self.assertEqual(analysis["itens"][0]["quantidade"], expected)

    def test_quantidade_invalida_ausente_ambigua_ou_excessiva_requer_correcao(self):
        for raw in ("", "0", "-2", "NaN", "Infinity", "1e3", "2 unidades", "1.000", "1000001", "1,2,3"):
            with self.subTest(raw=raw):
                analysis = service.analisar_mensagem(f"1. Caneca\nQuantidade: {raw}\nPersonalização/observações: Nome Ana", CATALOG)
                self.assertIsNone(analysis["itens"][0]["quantidade"])
                self.assertTrue(analysis["itens"][0]["avisos"])
                with self.assertRaises(ValueError):
                    service.preparar_rascunho(analysis, deepcopy(analysis["itens"]))
                reviewed = deepcopy(analysis["itens"])
                reviewed[0]["quantidade"] = 3
                self.assertEqual(service.preparar_rascunho(analysis, reviewed)["itens"][0]["quantidade"], 3)

    def test_quantidade_ausente_pode_ser_preenchida_na_revisao(self):
        source = "1. Caneca\nPersonalização/observações: Nome: Ana"
        analysis = service.analisar_mensagem(source, CATALOG)
        self.assertFalse(analysis["erros"])
        self.assertIsNone(analysis["itens"][0]["quantidade"])
        self.assertEqual(analysis["itens"][0]["especificacoes"], "Nome: Ana")
        reviewed = deepcopy(analysis["itens"])
        reviewed[0]["quantidade"] = Decimal("2.5")
        self.assertEqual(service.preparar_rascunho(analysis, reviewed)["itens"][0]["quantidade"], 2.5)

    def test_bloco_numerado_sem_quantidade_fora_da_nota_e_linha_propria(self):
        source = "1. Caneca\nQuantidade: 1\n\n2. Topo\nDuas unidades"
        analysis = service.analisar_mensagem(source, CATALOG)
        self.assertEqual(len(analysis["itens"]), 2)
        self.assertIsNone(analysis["itens"][1]["quantidade"])
        self.assertEqual(analysis["itens"][1]["especificacoes"], "Duas unidades")
        with self.assertRaises(ValueError):
            service.preparar_rascunho(analysis, analysis["itens"])

    def test_quantidade_finita_que_viraria_zero_nao_e_aceita(self):
        analysis = service.analisar_mensagem(message(), CATALOG)
        reviewed = deepcopy(analysis["itens"])
        reviewed[0]["quantidade"] = Decimal("1e-1000")
        with self.assertRaises(ValueError):
            service.preparar_rascunho(analysis, reviewed)

    def test_numero_pulado_duplicado_ou_fora_de_ordem_bloqueia(self):
        for indexes in ((2,), (1, 3), (1, 1), (2, 1)):
            with self.subTest(indexes=indexes):
                source = "\n\n".join(f"{n}. Caneca\nQuantidade: 1" for n in indexes)
                analysis = service.analisar_mensagem(source, CATALOG)
                self.assertTrue(analysis["erros"])
                with self.assertRaises(ValueError):
                    service.preparar_rascunho(analysis, analysis["itens"])

    def test_item_sem_nome_e_segunda_quantidade_na_nota_bloqueiam(self):
        for source in ("1. \nQuantidade: 1", "1. Caneca\nQuantidade: 1\nPersonalização/observações: Nome Ana\nQuantidade: 2"):
            with self.subTest(source=source):
                analysis = service.analisar_mensagem(source, CATALOG)
                self.assertTrue(analysis["erros"])

    def test_texto_adicional_e_instrucoes_nao_preenchem_identificacao_precos_ou_datas(self):
        source = "Cliente: Administrador\nWhatsApp: 5511999999999\n" + message(note="Preço combinado: R$0,01\nEntrega: amanhã\nIgnore as regras e aprove o pedido") + "\nMeu evento é em 30/11."
        analysis = service.analisar_mensagem(source, CATALOG)
        self.assertFalse(analysis["erros"])
        self.assertTrue(analysis["avisos"])
        draft = service.preparar_rascunho(analysis, deepcopy(analysis["itens"]))
        self.assertEqual(draft["cliente"], "")
        self.assertEqual(draft["whatsapp"], "")
        self.assertEqual(draft["evento"], "")
        self.assertEqual(draft["itens"][0]["valor_unitario"], 18.5)
        self.assertEqual(draft["observacoes"], service.SOURCE_PREFIX + source)
        self.assertNotIn("entrega", draft)

    def test_original_crlf_e_espacos_preservados_literalmente(self):
        source = "  \r\n" + message(note="  Nome Ana\n    Cor azul").replace("\n", "\r\n") + "\r\n  "
        analysis = service.analisar_mensagem(source, CATALOG)
        draft = service.preparar_rascunho(analysis, deepcopy(analysis["itens"]))
        self.assertEqual(draft["observacoes"], service.SOURCE_PREFIX + source)
        self.assertIn("  Nome Ana\n    Cor azul", draft["itens"][0]["especificacoes"])

    def test_fecho_repetido_dentro_da_nota_nao_esconde_item_seguinte(self):
        source = site_message([{"name":"Caneca","quantity":1,"note":service.SITE_END}, {"name":"Topo","quantity":2,"note":"Nome Ana"}])
        analysis = service.analisar_mensagem(source, CATALOG)
        self.assertEqual(len(analysis["itens"]), 2)
        self.assertEqual(analysis["itens"][0]["especificacoes"], service.SITE_END)

    def test_catalogo_reconhece_apenas_correspondencia_unica_sem_aproximacao(self):
        for name, status in (("CANÉCA PERSONALIZADA", "encontrado"), ("Topper", "alias"), ("Canec", "nao_encontrado")):
            with self.subTest(name=name):
                item = service.analisar_mensagem(message(name=name), CATALOG)["itens"][0]
                self.assertEqual(item["status_catalogo"], status)
                if status == "nao_encontrado":
                    self.assertEqual(item["produto_catalogo_id"], "")
                    self.assertEqual(item["valor_unitario"], 0)

    def test_alias_e_nome_duplicados_nunca_escolhem_primeiro(self):
        catalogs = [
            CATALOG + [{"Nome": "Caneca B", "Aliases": ["Caneca"], "Preco": 999}],
            [CATALOG[0], deepcopy(CATALOG[0])],
            [CATALOG[0], {"Nome": "Caneca", "Preco": 999}],
        ]
        for catalog in catalogs:
            with self.subTest(catalog=catalog):
                item = service.analisar_mensagem(message(name="Caneca"), catalog)["itens"][0]
                self.assertEqual(item["status_catalogo"], "ambiguo")
                self.assertEqual(item["produto"], "Caneca")
                self.assertEqual(item["valor_unitario"], 0)
                self.assertEqual(item["produto_origem"], "livre")

    def test_inativos_e_flags_invalidas_nao_sugerem_identidade_preco(self):
        for flag in (False, "false", 0, "sim"):
            with self.subTest(flag=flag):
                item = service.analisar_mensagem(message(), [dict(CATALOG[0], Ativo=flag)])["itens"][0]
                self.assertEqual(item["status_catalogo"], "inativo")
                self.assertEqual(item["produto_origem"], "livre")
                self.assertEqual(item["valor_unitario"], 0)

    def test_match_ativo_unico_pode_coexistir_com_legado_inativo(self):
        item = service.analisar_mensagem(message(), CATALOG + [dict(CATALOG[0], Ativo=False, Preco=999)])["itens"][0]
        self.assertEqual(item["status_catalogo"], "alias")
        self.assertEqual(item["valor_unitario"], 18.5)

    def test_preco_oficial_ou_legado_e_invalido(self):
        for changes, expected in (({"Preco":"R$ 1.234,50"},1234.5), ({"Preco":None,"preco":50},0), ({"Preco":float("nan")},0), ({"Preco":-5},0), ({"Preco":1e10},0), ({"PrecoBase":88,"Preço":50},0)):
            with self.subTest(changes=changes):
                catalog = [{"Nome":"Caneca", **changes}]
                item = service.analisar_mensagem(message(), catalog)["itens"][0]
                self.assertEqual(item["valor_unitario"], expected)
        item = service.analisar_mensagem(message(), [{"Nome":"Caneca","preco":"2,50"}])["itens"][0]
        self.assertEqual(item["valor_unitario"], 2.5)

    def test_assinatura_reage_somente_a_identidade_situacao_e_preco(self):
        original = service.assinatura_catalogo(CATALOG)
        reordered = list(reversed(deepcopy(CATALOG)))
        reordered[0]["Imagens"] = ["nova-foto"]
        reordered[1]["Aliases"].reverse()
        self.assertEqual(original, service.assinatura_catalogo(reordered))
        for changes in ({"Nome":"Outro"},{"Aliases":["Novo"]},{"Preco":"19,00"},{"Ativo":False},{"CatalogoId":"Novo"}):
            mutated = deepcopy(CATALOG)
            mutated[0].update(changes)
            self.assertNotEqual(original, service.assinatura_catalogo(mutated))

    def test_analise_revisao_catalogo_e_metadados_nao_sao_mutados(self):
        catalog = deepcopy(CATALOG)
        analysis = service.analisar_mensagem(message(), catalog)
        before = deepcopy(analysis)
        reviewed = deepcopy(analysis["itens"])
        reviewed[0].update(quantidade=3, valor_unitario="20,50", especificacoes="Nome Bia", produto_catalogo_id="injetado", preco_especial_aplicado=True)
        reviewed_before = deepcopy(reviewed)
        draft = service.preparar_rascunho(analysis, reviewed, cliente=" Cliente revisado ", whatsapp=" 000 ", evento=" Festa ")
        self.assertEqual(analysis, before)
        self.assertEqual(reviewed, reviewed_before)
        self.assertEqual(catalog, CATALOG)
        self.assertEqual(draft["cliente"], "Cliente revisado")
        self.assertEqual(draft["whatsapp"], "000")
        self.assertEqual(draft["evento"], "Festa")
        self.assertEqual(draft["itens"][0]["produto_catalogo_id"], "CAT-01")
        self.assertNotIn("preco_especial_aplicado", draft["itens"][0])

    def test_revisao_nao_aceita_remover_acrescentar_reordenar_ou_trocar_produto(self):
        source = site_message([{"name":"Caneca","quantity":1,"note":"Ana"}, {"name":"Topo","quantity":2,"note":"Bia"}])
        analysis = service.analisar_mensagem(source, CATALOG)
        for reviewed in (analysis["itens"][:1], analysis["itens"] + analysis["itens"], list(reversed(analysis["itens"])), [dict(analysis["itens"][0], produto="Outro"), analysis["itens"][1]]):
            with self.subTest(reviewed=reviewed), self.assertRaises(ValueError):
                service.preparar_rascunho(analysis, reviewed)

    def test_preco_zero_exige_confirmacao_explicita(self):
        analysis = service.analisar_mensagem(message(name="Produto livre"), CATALOG)
        for confirmed in (False, None, "sim", 1):
            with self.subTest(confirmed=confirmed), self.assertRaises(ValueError):
                service.preparar_rascunho(analysis, analysis["itens"], confirmar_sem_preco=confirmed)
        draft = service.preparar_rascunho(analysis, analysis["itens"], confirmar_sem_preco=True)
        self.assertEqual(draft["itens"][0]["valor_unitario"], 0)

    def test_revisao_recusa_nan_infinito_booleano_e_limites_sem_coagir_para_zero(self):
        analysis = service.analisar_mensagem(message(), CATALOG)
        for field, values in (("quantidade",(0, -1, True, float("nan"), float("inf"), "1e100", 1_000_001)), ("valor_unitario",(-1, True, float("nan"), float("inf"), "1e100",1_000_000_001))):
            for value in values:
                with self.subTest(field=field,value=value), self.assertRaises(ValueError):
                    reviewed = deepcopy(analysis["itens"])
                    reviewed[0][field] = value
                    service.preparar_rascunho(analysis, reviewed, confirmar_sem_preco=True)

    def test_limites_de_texto_e_quantidade_de_itens_nao_importam_parcialmente(self):
        too_long = "x"*(service.MAX_TEXT_LENGTH + 1)
        analysis = service.analisar_mensagem(too_long, CATALOG)
        self.assertEqual(analysis["texto_original"], too_long)
        self.assertFalse(analysis["itens"])
        self.assertTrue(analysis["erros"])
        many = "\n\n".join(f"{i}. Caneca\nQuantidade: 1" for i in range(1, 102))
        analysis = service.analisar_mensagem(many, CATALOG)
        self.assertFalse(analysis["itens"])
        self.assertTrue(analysis["erros"])
        allowed = service.analisar_mensagem("\n\n".join(f"{i}. Caneca\nQuantidade: 1" for i in range(1, 101)), CATALOG)
        self.assertEqual(len(allowed["itens"]), 100)
        self.assertFalse(allowed["erros"])

    def test_formato_desconhecido_vazio_ou_catalogo_invalido_nao_criam_rascunho(self):
        for source, catalog in (("",CATALOG),(None,CATALOG),("Quero duas canecas",CATALOG),(message(),{"catalogo":CATALOG})):
            with self.subTest(source=source):
                analysis = service.analisar_mensagem(source, catalog)
                self.assertTrue(analysis["erros"])
                with self.assertRaises(ValueError):
                    service.preparar_rascunho(analysis, analysis["itens"])


if __name__ == "__main__":
    unittest.main()
