from datetime import date
from produtividade_entregas_hf47 import indicadores, _data

def test_datas():
    assert _data('20/11/2026 12:15') == date(2026,11,20)
    assert _data('2026-11-20T12:15:00') == date(2026,11,20)
    assert _data('invalida') is None

def test_periodos_sem_sobreposicao():
    p=[{'numero_proposta':'1','aprovado':True,'pronto':True,'entregue':True,'aprovado_em':'10/11/2026','pronto_em':'19/11/2026','entregue_em':'20/11/2026','data_entrega':'20/11/2026'},
       {'numero_proposta':'2','aprovado':True,'pronto':True,'entregue':True,'pronto_em':'13/11/2026','entregue_em':'13/11/2026','data_entrega':'12/11/2026'},
       {'numero_proposta':'3','aprovado':True,'entregue':False,'data_entrega':'19/11/2026'},
       {'numero_proposta':'4','aprovado':True,'entregue':False,'data_entrega':'21/11/2026'},
       {'numero_proposta':'5','aprovado':True,'entregue':False},
       {'numero_proposta':'1','aprovado':True,'pronto':True,'entregue':True,'entregue_em':'20/11/2026'}]
    r=indicadores(p,hoje=date(2026,11,20),dias=7)
    assert (r['entregues'],r['entregues_anterior'],r['prontos']) == (1,1,1)
    assert (r['vencidos'],r['proximos_2_dias'],r['sem_prazo']) == (1,1,1)
    assert (r['entregas_com_prazo'],r['entregas_no_prazo'],r['mediana_dias_aprovacao_entrega']) == (1,1,10)

def test_nao_inventar_pontualidade():
    r=indicadores([{'numero_proposta':'1','entregue':True,'entregue_em':'20/11/2026'}],hoje=date(2026,11,20))
    assert r['entregues']==1 and r['entregas_com_prazo']==0 and r['mediana_dias_aprovacao_entrega'] is None
