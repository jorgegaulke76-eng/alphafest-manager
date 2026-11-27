"""HF65.24.49 — triagem diária de pedidos, somente leitura e sem novas consultas.

Partilha a fila normalizada da Central de Produção. Não grava dados,
não exige estoque e não interpreta uma entrega como horas de produção.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta
import unicodedata


def _data(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            return date.fromisoformat(v[:10])
        except ValueError:
            return None
    return None


def _normalizar(v):
    s = unicodedata.normalize('NFKD', str(v or ''))
    return ''.join(c for c in s if not unicodedata.combining(c)).casefold()


def plano_diario(fila, hoje: date | None = None):
    """Grupos mutuamente exclusivos e resumos para um quadro de ação."""
    hoje = hoje or date.today()
    grupos = {'Atrasados': [], 'Hoje': [], 'Amanhã': [], 'Sem prazo': [], 'Depois': []}
    vistos = set()
    for item in fila or []:
        if not isinstance(item, dict):
            continue
        numero = str(item.get('numero_proposta') or '').strip()
        chave = ('pedido', numero) if numero else ('obj', id(item))
        if chave in vistos:
            continue
        vistos.add(chave)
        entrega = _data(item.get('entrega_hf41'))
        if entrega is None:
            grupo = 'Sem prazo'
        elif entrega < hoje:
            grupo = 'Atrasados'
        elif entrega == hoje:
            grupo = 'Hoje'
        elif entrega == hoje + timedelta(days=1):
            grupo = 'Amanhã'
        else:
            grupo = 'Depois'
        fase = str(item.get('fase_hf41') or '')
        acao = ('Combinar retirada/entrega' if fase == 'pronto_entrega'
                else 'Revisar a etapa do pedido' if fase == 'sem_registro'
                else 'Conferir produção e prazo')
        grupos[grupo].append({**item, 'grupo_hf49': grupo, 'acao_hf49': acao})
    for chave in grupos:
        grupos[chave].sort(key=lambda x: (_data(x.get('entrega_hf41')) or date.max,
                                         str(x.get('numero_proposta') or '')))
    return {'hoje': hoje, 'grupos': grupos, 'total_urgente': sum(len(grupos[k]) for k in ('Atrasados','Hoje','Amanhã')),
            'prontos_urgentes': sum(x.get('fase_hf41') == 'pronto_entrega' for k in ('Atrasados','Hoje','Amanhã') for x in grupos[k]),
            'sem_prazo': len(grupos['Sem prazo'])}


def filtrar(itens, busca=''):
    termo = _normalizar(busca).strip()
    if not termo:
        return list(itens or [])
    return [x for x in itens or [] if termo in _normalizar(' '.join(str(x.get(c) or '') for c in ('numero_proposta','cliente_nome','resumo_produtos')))]
