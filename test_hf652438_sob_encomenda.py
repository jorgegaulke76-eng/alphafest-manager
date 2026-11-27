"""HF65.24.38: regression checks for made-to-order commercial workflow."""
from datetime import date
from central_operational_runtime import montar_snapshot_operacional


def _proposta(numero, *, aprovado=True, pronto=False, entregue=False, prazo='20/11/2026'):
    return {
        'numero_proposta': numero, 'cliente_nome': 'Cliente exemplo',
        'aprovado': aprovado, 'pronto': pronto, 'entregue': entregue,
        'data_entrega': prazo,
        'itens': [{'produto': 'Caneca personalizada', 'quantidade': 2}],
    }


def test_central_sem_estoque_aprovado_pode_iniciar():
    propostas = [_proposta('001'), _proposta('002', pronto=True),
                 _proposta('003', entregue=True, pronto=True),
                 _proposta('004', aprovado=False)]
    tarefas = [
        {'numero_proposta': '001', 'status': 'Pronto para produzir', 'ativa': True, 'id': 'T1'},
        {'numero_proposta': '002', 'status': 'Pronto', 'ativa': True, 'id': 'T2'},
    ]
    resultado = montar_snapshot_operacional(propostas, tarefas, [], {}, [], date(2026, 11, 19),
                                           sob_encomenda=True)
    por_numero = {item['numero_proposta']: item for item in resultado['central_producao']}
    assert set(por_numero) == {'001', '002'}
    assert por_numero['001']['pode_iniciar_producao'] is True
    assert por_numero['001']['material_liberado'] is True
    assert por_numero['002']['pode_iniciar_producao'] is False
    assert por_numero['002']['situacao_operacional_chave'] == 'pronto_entrega'
    assert all(item['pendencias'] == [] for item in resultado['previsao'])


def test_status_vencido_usa_prazo_nao_estoque():
    resultado = montar_snapshot_operacional(
        [_proposta('001', prazo='17/11/2026'), _proposta('002', pronto=True, prazo='17/11/2026')],
        [], [], {}, [], date(2026, 11, 19), sob_encomenda=True,
    )
    previsao = {item['numero_proposta']: item for item in resultado['previsao']}
    assert previsao['001']['risco_atraso'] is True
    assert previsao['001']['motivos'] == ['prazo de entrega vencido']
    assert previsao['002']['risco_atraso'] is False


def test_fluxo_legado_permanece_compativel():
    # The legacy signature is still accepted and retains its own material rules.
    resultado = montar_snapshot_operacional([_proposta('001')], [], [], {}, [],
                                           date(2026, 11, 19))
    assert len(resultado['previsao']) == 1
