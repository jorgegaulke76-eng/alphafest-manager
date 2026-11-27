from datetime import date, timedelta
from planejamento_semanal_hf48 import planejar


def test_planejamento_semana():
    hoje = date(2026, 11, 20)
    def ped(n, data):
        return {'numero_proposta': str(n), 'cliente_nome': 'Cliente', 'entrega_hf41': data}
    dados = [ped(1, hoje-timedelta(days=2)), ped(2, hoje), ped(3, hoje),
             ped(4, hoje+timedelta(days=6)), ped(5, hoje+timedelta(days=7)),
             ped(6, None), ped(2, hoje)]
    r = planejar(dados, hoje)
    assert len(r['dias']) == 7
    assert r['total_semana'] == 3
    assert r['dias_com_entregas'] == 2
    assert r['pico'] == 2
    assert len(r['vencidos']) == 1
    assert len(r['sem_data']) == 1
    assert len(r['fora_periodo']) == 1
    assert r['dias'][0]['total'] == 2
    assert r['dias'][-1]['total'] == 1
    assert sum(map(len,(r['vencidos'],r['sem_data'],r['fora_periodo'])))+r['total_semana'] == 6


def test_sem_entradas():
    r = planejar([], date(2026, 11, 20))
    assert r['total_semana'] == r['pico'] == r['dias_com_entregas'] == 0
    assert len(r['dias']) == 7
