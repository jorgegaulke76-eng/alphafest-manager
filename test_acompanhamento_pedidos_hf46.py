from datetime import date
from acompanhamento_pedidos_hf46 import acompanhar, filtrar

def test_resumo():
    hoje=date(2026,11,20)
    base=[
        {'numero_proposta':'1','status':'Aguardando aprovação','data_entrega':'19/11/2026'},
        {'numero_proposta':'2','status':'Aprovado','data_entrega':'20/11/2026'},
        {'numero_proposta':'3','status':'Pronto / aguardando retirada ou entrega','data_entrega':'21/11/2026'},
        {'numero_proposta':'1','status':'Aguardando aprovação','data_entrega':'19/11/2026'},
    ]
    r,f=acompanhar(base,hoje)
    assert r=={'abertos':3,'aguardando_aprovacao':1,'prazo_vencido':1,'entrega_hoje':1,'prontos':1}
    assert len(filtrar(f,'Prazo vencido'))==1
    assert f[0]['numero']=='1'
    assert f[1]['numero']=='2'

def test_dates_and_missing():
    r,f=acompanhar([{'numero_proposta':'4','status':'Aprovado','data_entrega':'2026-11-22'}, {'numero_proposta':'5','status':'Aprovado'}],date(2026,11,20))
    assert r['abertos']==2
    assert f[0]['entrega_texto']=='22/11/2026'
    assert f[1]['entrega_texto']=='Sem data'
