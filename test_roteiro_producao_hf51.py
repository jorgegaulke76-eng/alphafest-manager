from datetime import date
import csv
import io
import unittest

from planejamento_diario_hf49 import plano_diario
from planejamento_semanal_hf48 import planejar
from roteiro_producao_hf51 import roteiro_diario, agenda_semanal_csv


class TestRoteiroHF51(unittest.TestCase):
    def setUp(self):
        self.hoje = date(2026, 11, 20)
        self.fila = [
            {'numero_proposta':'A01','cliente_nome':'Ana','resumo_produtos':'Caneca personalizada',
             'fase_hf41':'preparacao','fase_nome_hf41':'Preparação / arte',
             'entrega_hf41':date(2026,11,19),'data_texto_hf41':'19/11/2026'},
            {'numero_proposta':'A02','cliente_nome':'Beto','resumo_produtos':'Topo de bolo',
             'fase_hf41':'pronto_entrega','fase_nome_hf41':'Pronto para entrega',
             'entrega_hf41':self.hoje,'data_texto_hf41':'20/11/2026'},
            {'numero_proposta':'A03','cliente_nome':'Carla','resumo_produtos':'Caixa personalizada',
             'fase_hf41':'preparacao','fase_nome_hf41':'Preparação / arte',
             'entrega_hf41':None,'data_texto_hf41':'Sem data'},
            {'numero_proposta':'A04','cliente_nome':'David','resumo_produtos':'Tag personalizada',
             'fase_hf41':'preparacao','fase_nome_hf41':'Preparação / arte',
             'entrega_hf41':date(2026,11,25),'data_texto_hf41':'25/11/2026'},
        ]

    def test_daily_text_groups_are_accurate(self):
        txt = roteiro_diario(plano_diario(self.fila,hoje=self.hoje))
        self.assertIn('ATRASADOS — 1 pedido(s)',txt)
        self.assertIn('HOJE — 1 pedido(s)',txt)
        self.assertIn('SEM PRAZO — 1 pedido(s)',txt)
        self.assertIn('Combinar retirada/entrega',txt)
        self.assertIn('A01',txt)
        self.assertNotIn('A04',txt)  # Depois is not an urgent action

    def test_commercial_return_is_explicit_and_private(self):
        plano = plano_diario(self.fila,hoje=self.hoje)
        ret=[{'numero_proposta':'R01','cliente_nome':'Eva','nivel':'alta','acao':'Retornar contato',
              'whatsapp':'5511911111111','mensagem_sugerida':'Contato privado'},
             {'numero_proposta':'R02','cliente_nome':'Fê','nivel':'aguardar','acao':'Não cobrar'}]
        normal=roteiro_diario(plano,retornos=ret)
        self.assertNotIn('RETORNOS COMERCIAIS',normal)
        priv=roteiro_diario(plano,retornos=ret,incluir_retornos=True)
        self.assertIn('R01',priv)
        self.assertNotIn('R02',priv)
        self.assertNotIn('55119',priv)
        self.assertNotIn('Contato privado',priv)

    def test_week_csv_includes_overdue_no_date_and_day(self):
        sem=planejar(self.fila, hoje=self.hoje)
        csv_data=agenda_semanal_csv(sem)
        self.assertTrue(csv_data.startswith(b'\xef\xbb\xbf'))
        rows=list(csv.reader(io.StringIO(csv_data.decode('utf-8-sig')),delimiter=';'))
        self.assertEqual(len(rows),5)
        self.assertEqual({x[2] for x in rows[1:]},{'A01','A02','A03','A04'})
        self.assertEqual(next(x[0] for x in rows if x[2]=='A01'),'Prazo vencido')
        self.assertEqual(next(x[0] for x in rows if x[2]=='A03'),'Sem prazo')

    def test_csv_escape_spreadsheet_formulas(self):
        itens=[dict(self.fila[0], cliente_nome='=HYPERLINK("unsafe")',resumo_produtos='+SUM(1,2)')]
        csv_data=agenda_semanal_csv(planejar(itens, hoje=self.hoje)).decode('utf-8-sig')
        self.assertIn("'=HYPERLINK",csv_data)
        self.assertIn("'+SUM",csv_data)

    def test_exports_do_not_mutate_data(self):
        import copy
        src=copy.deepcopy(self.fila)
        plano=plano_diario(self.fila,hoje=self.hoje)
        semana=planejar(self.fila,hoje=self.hoje)
        roteiro_diario(plano)
        agenda_semanal_csv(semana)
        self.assertEqual(self.fila,src)

    def test_limit_guards(self):
        with self.assertRaises(ValueError):
            roteiro_diario({},limite_por_grupo=0)

if __name__=='__main__': unittest.main()
