from datetime import date
from central_producao_painel_hf41 import preparar_fila, resumo_fila, filtrar_fila

HOJE=date(2026,11,20)
DADOS=[
 {'numero_proposta':'10','cliente_nome':'Ana','resumo_produtos':'Caneca Azul','situacao_operacional_chave':'preparacao','data_entrega':'2026-11-19'},
 {'numero_proposta':'11','cliente_nome':'Beto','resumo_produtos':'Convite','situacao_operacional_chave':'pronto_iniciar','data_entrega':'2026-11-20'},
 {'numero_proposta':'12','cliente_nome':'Carla','resumo_produtos':'Balão','situacao_operacional_chave':'em_producao','data_entrega':'2026-11-22'},
 {'numero_proposta':'13','cliente_nome':'Davi','resumo_produtos':'Topo','situacao_operacional_chave':'pronto_entrega','data_entrega':'2026-12-01'},
 {'numero_proposta':'14','cliente_nome':'Eva','resumo_produtos':'Adesivo','situacao_operacional_chave':'aguardando_material','data_entrega':None},
]

def test_prazos():
 f=preparar_fila(DADOS,HOJE)
 assert [x['numero_proposta'] for x in f]==['10','11','12','13','14']
 assert [x['prioridade_hf41'] for x in f]==[0,1,2,3,3]
 assert f[-1]['fase_nome_hf41']=='Revisar etapa'

def test_totais():
 r=resumo_fila(preparar_fila(DADOS,HOJE))
 assert r['total']==5 and r['atrasados']==1 and r['hoje']==1
 assert r['preparacao']==r['iniciar']==r['producao']==r['prontos']==r['revisar']==1

def test_filtros():
 f=preparar_fila(DADOS,HOJE)
 assert len(filtrar_fila(f,'CANÉCA'))==1
 assert len(filtrar_fila(f,'','Em produção'))==1
 assert len(filtrar_fila(f,prazo='Sem data'))==1
 assert len(filtrar_fila(f,prazo='Atrasados'))==1

def test_sem_mutacao():
 original=[dict(x) for x in DADOS]
 preparar_fila(DADOS,HOJE)
 assert DADOS==original

if __name__=='__main__':
 for t in (test_prazos,test_totais,test_filtros,test_sem_mutacao):
  t()
 print('4 testes HF41 OK')
