from datetime import date, timedelta
from planejamento_diario_hf49 import plano_diario, filtrar

HOJE = date(2026, 11, 20)

def ped(n, prazo, fase='em_producao', cliente='João'):
    return {'numero_proposta': str(n), 'entrega_hf41': prazo, 'fase_hf41': fase,
            'cliente_nome': cliente, 'resumo_produtos': 'Caneca personalizada'}

def test_grupos_sem_duplicar():
    a = ped(1, HOJE-timedelta(days=1))
    fila = [a, ped(2, HOJE), ped(3, HOJE+timedelta(days=1),'pronto_entrega'),
            ped(4,None),ped(5,HOJE+timedelta(days=3)),a]
    r = plano_diario(fila, HOJE)
    assert [len(r['grupos'][k]) for k in ('Atrasados','Hoje','Amanhã','Sem prazo','Depois')] == [1,1,1,1,1]
    assert r['total_urgente'] == 3 and r['prontos_urgentes'] == 1 and r['sem_prazo'] == 1
    assert r['grupos']['Amanhã'][0]['acao_hf49'] == 'Combinar retirada/entrega'

def test_busca_acentos_e_vazios():
    itens = [ped(6, HOJE, cliente='José'), ped(7,HOJE,cliente='Maria')]
    assert len(filtrar(itens,'jose')) == 1
    assert len(filtrar(itens,'caneca')) == 2
    assert plano_diario([],HOJE)['total_urgente'] == 0

def test_entradas_invalidas_e_anonimas():
    itens = [ped(1,'2026-11-20'), ped(2,'data inválida'), {}, {}, None]
    r = plano_diario(itens, HOJE)
    assert len(r['grupos']['Hoje']) == 1
    assert len(r['grupos']['Sem prazo']) == 3
