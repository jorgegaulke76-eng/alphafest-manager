import unittest

from relacionamentos_service import (
    chave_cliente,
    localizar_cliente_comercial,
    localizar_relacionamento,
    relacionamento_da_proposta,
    proposta_com_dados_atuais,
    propostas_do_cliente,
    pontuacao_cadastro_relacionamento,
    proxima_acao_crm,
    proxima_acao_proposta,
    telefone_chave,
)


class RelacionamentosServiceTests(unittest.TestCase):
    def setUp(self):
        self.clientes = [
            {"id": "C1", "nome": "Cliente Um", "documento": "123.456.789-00", "whatsapp": "(11) 99999-0001", "email": "novo@x.com", "cidade": "Itatiba"},
            {"id": "C2", "nome": "Cliente Dois", "documento": "", "whatsapp": "11 98888-0002"},
        ]

    def test_chave_cliente_preserva_precedencia_documento_whatsapp_nome(self):
        self.assertEqual(chave_cliente("A", "123.456", "11999990000"), "doc:123456")
        self.assertEqual(chave_cliente("A", "", "11 99999-0000"), "wa:11999990000")
        self.assertEqual(chave_cliente("  Maria   Silva  "), "nome:maria silva")

    def test_telefone_chave_preserva_ultimos_11_digitos(self):
        self.assertEqual(telefone_chave("+55 (11) 99999-0001"), "11999990001")

    def test_localizacao_comercial_prioriza_documento(self):
        achado = localizar_cliente_comercial(self.clientes, nome="Outro", documento="12345678900", whatsapp="000")
        self.assertEqual(achado["id"], "C1")

    def test_localizacao_relacional_prioriza_whatsapp_e_faz_fallback_nome(self):
        self.assertEqual(localizar_relacionamento(self.clientes, nome="Errado", whatsapp="11988880002")["id"], "C2")
        self.assertEqual(localizar_relacionamento(self.clientes, nome="Cliente Um", whatsapp="")["id"], "C1")

    def test_relacionamento_id_vence_fallback(self):
        prop = {"relacionamento_id": "C2", "cliente_nome": "Cliente Um", "whatsapp": "11999990001"}
        self.assertEqual(relacionamento_da_proposta(prop, self.clientes)["id"], "C2")

    def test_visao_atualiza_contato_sem_alterar_itens_valores_status(self):
        prop = {
            "relacionamento_id": "C1", "cliente_nome": "Nome antigo", "whatsapp": "111",
            "itens": [{"produto": "PAPEL DE ARROZ", "quantidade": 1}], "valor_total": 10.0,
            "aprovado": True, "entregue": True,
        }
        visao, atual = proposta_com_dados_atuais(prop, self.clientes)
        self.assertEqual(atual["id"], "C1")
        self.assertEqual(visao["cliente_nome"], "Cliente Um")
        self.assertEqual(visao["email"], "novo@x.com")
        self.assertEqual(visao["itens"], prop["itens"])
        self.assertEqual(visao["valor_total"], 10.0)
        self.assertTrue(visao["aprovado"])
        self.assertTrue(visao["entregue"])
        self.assertEqual(prop["cliente_nome"], "Nome antigo")

    def test_propostas_do_cliente_aceita_id_e_fallback_legado(self):
        hist = [
            {"numero_proposta": "P1", "relacionamento_id": "C1"},
            {"numero_proposta": "P2", "cliente_nome": "Cliente Um", "documento": "12345678900"},
            {"numero_proposta": "P3", "cliente_nome": "Outro"},
        ]
        numeros = [p["numero_proposta"] for p in propostas_do_cliente(self.clientes[0], hist)]
        self.assertEqual(numeros, ["P1", "P2"])

    def test_pontuacao_prefere_cadastro_manual_completo(self):
        historico = {"nome": "Cliente", "origem": "Histórico de propostas"}
        manual = {"nome": "Cliente", "origem": "Cadastro manual", "whatsapp": "11999990000", "email": "x@y.com", "politica_atendimento": {"nivel": "Normal"}}
        self.assertGreater(pontuacao_cadastro_relacionamento(manual), pontuacao_cadastro_relacionamento(historico))

    def test_pos_venda_vem_de_status_entregue(self):
        self.assertEqual(proxima_acao_proposta({"aprovado": True, "entregue": True}), "Registrar pós-venda")
        self.assertEqual(proxima_acao_crm({"status": "Entregue"}), "Fazer pós-venda")
        self.assertEqual(proxima_acao_crm({"status": "Pós-venda"}), "Registrar retorno e oportunidade futura")


if __name__ == "__main__":
    unittest.main()
