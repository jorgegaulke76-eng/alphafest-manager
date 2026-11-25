"""HF65.24.58 - validação offline da ficha e da confirmação explícita."""
import unittest
from datetime import datetime
from ficha_producao_hf58 import (situacao_arte, registrar_aprovacao, ficha_producao_txt,
    identidade_conferencia_arte, registrar_aprovacao_conferida)

NOW = datetime(2026, 11, 25, 13, 20)


def projeto():
    return {"arquivos": [{"id":"AR1", "nome":"Ana_v1.png", "categoria":"Arte", "arquivado":False}],
            "tema":"Jardim", "observacoes":"usar fita azul"}


class FichaHF58Tests(unittest.TestCase):
    def test_sem_arte(self):
        self.assertEqual(situacao_arte({})[0], 'sem_arte')

    def test_aprovacao_explicita_e_ficha(self):
        p = registrar_aprovacao(projeto(), 'AR1', 'Anna', NOW)
        self.assertEqual(situacao_arte(p)[0], 'aprovada')
        pedido = {"numero_proposta":"123", "cliente_nome":"Cliente", "data_entrega":"30/11/2026",
                  "itens":[{"produto":"Caneca", "quantidade":2, "especificacoes":"Nome Ana"},
                           {"produto":"Caneca", "quantidade":1, "especificacoes":"Nome Pedro"}]}
        texto = ficha_producao_txt(pedido, p, NOW).decode('utf-8-sig')
        self.assertIn('Nome Ana', texto)
        self.assertIn('Nome Pedro', texto)
        self.assertIn('Ana_v1.png', texto)
        self.assertNotIn('R$', texto)

    def test_arte_nova_invalida_anterior(self):
        p = registrar_aprovacao(projeto(), 'AR1', 'Jorge', NOW)
        p['arquivos'].append({'id':'AR2','nome':'Ana_v2.png','categoria':'Arte','arquivado':False})
        self.assertEqual(situacao_arte(p)[0], 'revisao_pendente')
        self.assertIn('REVISÃO PENDENTE', ficha_producao_txt({}, p, NOW).decode('utf-8-sig'))
        p['arquivos'][-1]['arquivado'] = True
        self.assertEqual(situacao_arte(p)[0], 'revisao_pendente')
        p = registrar_aprovacao(p, 'AR1', 'Jorge', NOW)
        self.assertEqual(situacao_arte(p)[0], 'aprovada')

    def test_substituir_arquivo_sem_mudar_id_exige_nova_confirmacao(self):
        p = registrar_aprovacao(projeto(), 'AR1', 'Anna', NOW)
        p['arquivos'][0]['url'] = 'https://exemplo.invalid/arte-corrigida.png'
        self.assertEqual(situacao_arte(p)[0], 'revisao_pendente')
        p = registrar_aprovacao(p, 'AR1', 'Anna', NOW)
        self.assertEqual(situacao_arte(p)[0], 'aprovada')
        p['arquivos'][0]['nome'] = 'Ana_v2.png'
        self.assertEqual(situacao_arte(p)[0], 'revisao_pendente')

    def test_registro_antigo_sem_assinatura_exige_reconfirmacao(self):
        p = registrar_aprovacao(projeto(), 'AR1', 'Anna', NOW)
        del p['aprovacao_arte_hf58']['assinatura_arquivo']
        self.assertEqual(situacao_arte(p)[0], 'revisao_pendente')

    def test_arquivo_aprovado_arquivado_invalida(self):
        p = registrar_aprovacao(projeto(), 'AR1', 'Jorge', NOW)
        p['arquivos'][0]['arquivado'] = True
        self.assertEqual(situacao_arte(p)[0], 'sem_arte')

    def test_rejeita_sem_responsavel_ou_arquivo(self):
        with self.assertRaises(ValueError):
            registrar_aprovacao(projeto(), 'AR1', '', NOW)
        with self.assertRaises(ValueError):
            registrar_aprovacao(projeto(), 'X', 'Anna', NOW)

    def test_identidade_interface_muda_mesmo_se_id_se_mantiver(self):
        p = projeto()
        p['id'] = 'PROJETO-1'
        primeira = identidade_conferencia_arte(p)
        self.assertEqual(primeira, identidade_conferencia_arte(p))
        p['arquivos'][0]['url'] = 'https://exemplo.invalid/arte-v2.png'
        segunda = identidade_conferencia_arte(p)
        self.assertNotEqual(primeira, segunda)
        p['arquivos'].append({'id':'AR2','nome':'Nova.png','categoria':'Arte','arquivado':False})
        terceira = identidade_conferencia_arte(p)
        self.assertNotEqual(segunda, terceira)
        p['arquivos'][-1]['arquivado'] = True
        self.assertNotEqual(terceira, identidade_conferencia_arte(p))

    def test_aprovacao_confere_estado_exibido_com_fonte_atual(self):
        exibido = projeto()
        exibido['id'] = 'PROJETO-1'
        atual = {**exibido, 'observacoes': 'Alteração salva por outra pessoa'}
        p = registrar_aprovacao_conferida(exibido, atual, 'AR1', 'Anna', NOW)
        self.assertEqual(p['observacoes'], 'Alteração salva por outra pessoa')
        self.assertEqual(situacao_arte(p)[0], 'aprovada')
        atual['arquivos'] = [{**exibido['arquivos'][0], 'nome': 'Nova_arte.png'}]
        with self.assertRaisesRegex(ValueError, 'arte mudou'):
            registrar_aprovacao_conferida(exibido, atual, 'AR1', 'Anna', NOW)
        with self.assertRaisesRegex(ValueError, 'arte mudou'):
            registrar_aprovacao_conferida(exibido, None, 'AR1', 'Anna', NOW)
        with self.assertRaisesRegex(ValueError, 'arte mudou'):
            registrar_aprovacao_conferida(exibido, {**exibido, 'id': 'OUTRO'}, 'AR1', 'Anna', NOW)

    def test_ficha_nao_trunca_personalizacoes_e_observacoes_longas(self):
        esp = 'Nome Ana; ' + 'pormenor-' * 480 + ' CONFERIR FIM DAS ESPECIFICAÇÕES'
        obs = 'urgente ' * 430 + ' CONFERIR FIM DAS OBSERVAÇÕES'
        p = projeto()
        p['observacoes'] = obs
        texto = ficha_producao_txt({'itens':[{'produto':'Caneca', 'quantidade':1,
                                           'especificacoes':esp}]},p,NOW).decode('utf-8-sig')
        self.assertIn('CONFERIR FIM DAS ESPECIFICAÇÕES', texto)
        self.assertIn('CONFERIR FIM DAS OBSERVAÇÕES', texto)

    def test_ficha_sem_pedido(self):
        texto = ficha_producao_txt({}, {}, NOW).decode('utf-8-sig')
        self.assertIn('SEM ARTE CADASTRADA', texto)
        self.assertIn('não informado', texto)

if __name__ == '__main__':
    unittest.main()
