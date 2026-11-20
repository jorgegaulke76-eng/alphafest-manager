"""HF65.24.46 — resumo operacional somente leitura para pedidos abertos.

Reaproveita linhas da Agenda da Anna já normalizadas. Não altera dados,
não acessa estoque nem consulta o banco e não infere aprovação de arte.
"""
from __future__ import annotations
from datetime import date, datetime
from typing import Iterable


def _data(valor):
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(str(valor or '')[:10], fmt).date()
        except (ValueError, TypeError):
            pass
    return None


def acompanhar(linhas: Iterable[dict], hoje: date | None = None):
    """Retorna contagens e fila sem duplicar pedidos ou assumir situação de pagamento."""
    hoje = hoje or date.today()
    registros = {}
    for idx, dado in enumerate(linhas or []):
        if not isinstance(dado, dict):
            continue
        numero = str(dado.get('numero_proposta') or '').strip()
        chave = numero or f'sem-numero-{idx}'
        if chave in registros:
            continue
        status = str(dado.get('status') or '')
        entrega = _data(dado.get('data_entrega_obj') or dado.get('data_entrega'))
        aguardando = 'Aguardando aprovação' in status
        pronto = 'Pronto / aguardando retirada ou entrega' in status
        vencido = bool(entrega and entrega < hoje)
        hoje_entrega = bool(entrega == hoje)
        if vencido:
            grupo = 'Prazo vencido'
            nivel = 0
        elif hoje_entrega:
            grupo = 'Entrega hoje'
            nivel = 1
        elif pronto:
            grupo = 'Pronto para entrega'
            nivel = 2
        elif aguardando:
            grupo = 'Aguardando aprovação'
            nivel = 3
        else:
            grupo = 'Acompanhamento'
            nivel = 4
        registros[chave] = {
            'numero': numero,
            'cliente': str(dado.get('cliente_nome') or 'Cliente'),
            'produtos': str(dado.get('produtos') or ''),
            'status': status,
            'entrega': entrega,
            'entrega_texto': entrega.strftime('%d/%m/%Y') if entrega else 'Sem data',
            'grupo': grupo,
            'nivel': nivel,
            'aguardando': aguardando,
            'pronto': pronto,
            'vencido': vencido,
            'hoje': hoje_entrega,
        }
    fila = sorted(registros.values(), key=lambda d: (d['nivel'], d['entrega'] or date.max, d['numero']))
    resumo = {
        'abertos': len(fila),
        'aguardando_aprovacao': sum(d['aguardando'] for d in fila),
        'prazo_vencido': sum(d['vencido'] for d in fila),
        'entrega_hoje': sum(d['hoje'] for d in fila),
        'prontos': sum(d['pronto'] for d in fila),
    }
    return resumo, fila


def filtrar(fila, categoria='Todas'):
    filtros = {
        'Aguardando aprovação': lambda d: d['aguardando'],
        'Prazo vencido': lambda d: d['vencido'],
        'Entrega hoje': lambda d: d['hoje'],
        'Pronto para entrega': lambda d: d['pronto'],
    }
    predicado = filtros.get(categoria)
    return [d for d in fila if predicado(d)] if predicado else list(fila)
