"""HF65.24.41 — leitura leve de produção sob encomenda.

A fila não persiste status e não lê materiais; datas e etapas são derivadas da
central já montada. O andamento continua controlado nos fluxos oficiais.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Iterable
import unicodedata

FASES = {
    'pronto_iniciar': 'Para iniciar',
    'em_producao': 'Em produção',
    'preparacao': 'Preparação / arte',
    'pronto_entrega': 'Pronto para entrega',
    'sem_registro': 'Revisar etapa',
}


def _date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        try:
            return datetime.strptime(str(value)[:10], '%d/%m/%Y').date()
        except (TypeError, ValueError):
            return None


def _norm(value):
    txt = unicodedata.normalize('NFKD', str(value or ''))
    return ''.join(c for c in txt if not unicodedata.combining(c)).casefold()


def preparar_fila(linhas: Iterable[dict], hoje: date | None = None) -> list[dict]:
    hoje = hoje or date.today()
    saida = []
    for original in linhas or ():
        if not isinstance(original, dict):
            continue
        item = dict(original)
        fase = str(item.get('situacao_operacional_chave') or 'sem_registro')
        if fase not in FASES:
            # Em sob encomenda, uma situação legada de material não deve virar trava.
            fase = 'sem_registro'
        entrega = _date(item.get('data_entrega') or item.get('data_entrega_original'))
        dias = (entrega - hoje).days if entrega else None
        if dias is None:
            prazo = 'Sem data'
            prioridade = 3
        elif dias < 0:
            prazo = f'{abs(dias)} dia(s) em atraso'
            prioridade = 0
        elif dias == 0:
            prazo = 'Entrega hoje'
            prioridade = 1
        elif dias <= 2:
            prazo = f'Entrega em {dias} dia(s)'
            prioridade = 2
        else:
            prazo = f'Entrega em {dias} dia(s)'
            prioridade = 3
        item.update({
            'fase_hf41': fase, 'fase_nome_hf41': FASES[fase],
            'entrega_hf41': entrega, 'prazo_hf41': prazo,
            'prioridade_hf41': prioridade,
            'data_texto_hf41': entrega.strftime('%d/%m/%Y') if entrega else 'Sem data',
        })
        saida.append(item)
    saida.sort(key=lambda x: (
        x['prioridade_hf41'],
        x['entrega_hf41'] or date.max,
        str(x.get('numero_proposta') or ''),
    ))
    return saida


def resumo_fila(linhas: Iterable[dict]) -> dict[str, int]:
    linhas = list(linhas or [])
    return {
        'total': len(linhas),
        'preparacao': sum(x['fase_hf41'] == 'preparacao' for x in linhas),
        'iniciar': sum(x['fase_hf41'] == 'pronto_iniciar' for x in linhas),
        'producao': sum(x['fase_hf41'] == 'em_producao' for x in linhas),
        'prontos': sum(x['fase_hf41'] == 'pronto_entrega' for x in linhas),
        'revisar': sum(x['fase_hf41'] == 'sem_registro' for x in linhas),
        'atrasados': sum(x['prioridade_hf41'] == 0 for x in linhas),
        'hoje': sum(x['prioridade_hf41'] == 1 for x in linhas),
        'sem_data': sum(x['entrega_hf41'] is None for x in linhas),
    }


def filtrar_fila(linhas, busca='', fase='Todas', prazo='Todos'):
    termo = _norm(busca).strip()
    retorno = []
    for x in linhas:
        if termo and termo not in _norm(' '.join(str(x.get(k) or '') for k in ('numero_proposta','cliente_nome','resumo_produtos'))):
            continue
        if fase != 'Todas' and x['fase_nome_hf41'] != fase:
            continue
        p = x['prioridade_hf41']
        if prazo == 'Atrasados' and p != 0:
            continue
        if prazo == 'Hoje' and p != 1:
            continue
        if prazo == 'Próximos 2 dias' and p != 2:
            continue
        if prazo == 'Sem data' and x['entrega_hf41'] is not None:
            continue
        retorno.append(x)
    return retorno
