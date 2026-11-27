"""HF65.24.47 — produtividade por marcos oficiais; somente leitura.

Não confunde datas previstas com conclusão efetiva nem atribui atrasos
quando o registro de entrega não possui carimbo confiável.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta
from statistics import median
from proposal_status import status_bool


def _data(v):
    if isinstance(v, datetime): return v.date()
    if isinstance(v, date): return v
    s = str(v or '').strip()
    if not s: return None
    for fragment in (s, s[:19], s[:10]):
        for fmt in ('%d/%m/%Y %H:%M:%S','%d/%m/%Y %H:%M','%d/%m/%Y','%Y-%m-%dT%H:%M:%S','%Y-%m-%d %H:%M:%S','%Y-%m-%d'):
            try: return datetime.strptime(fragment, fmt).date()
            except (TypeError, ValueError): pass
    try: return datetime.fromisoformat(s.replace('Z','+00:00')).date()
    except (ValueError, TypeError): return None


def indicadores(propostas, hoje=None, dias=7):
    hoje = hoje or date.today()
    inicio = hoje-timedelta(days=dias-1)
    anterior_inicio = inicio-timedelta(days=dias)
    anterior_fim = inicio-timedelta(days=1)
    unicos = {}
    for i,p in enumerate(propostas or []):
        if not isinstance(p,dict): continue
        chave = str(p.get('numero_proposta') or '').strip() or f'_sem_numero_{i}'
        if chave not in unicos: unicos[chave]=p
    pedidos = list(unicos.items())
    def contar(chave, a, b):
        return sum(1 for _,p in pedidos if status_bool(p,chave) and (d:=_data(p.get(chave+'_em'))) and a<=d<=b)
    prontas = contar('pronto',inicio,hoje)
    entregues = contar('entregue',inicio,hoje)
    prontas_ant = contar('pronto',anterior_inicio,anterior_fim)
    entregues_ant = contar('entregue',anterior_inicio,anterior_fim)
    duracoes=[]; avaliaveis=[]; recentes=[]
    for numero,p in pedidos:
        if not status_bool(p,'entregue'): continue
        d=_data(p.get('entregue_em'))
        if not d or not inicio<=d<=hoje: continue
        previsto=_data(p.get('data_entrega'))
        if previsto: avaliaveis.append(d<=previsto)
        a=_data(p.get('aprovado_em'))
        if a and a<=d: duracoes.append((d-a).days)
        recentes.append({'numero':numero, 'cliente':str(p.get('cliente_nome') or p.get('cliente') or 'Cliente'), 'entregue':d,'previsto':previsto,'situacao':'No prazo' if previsto and d<=previsto else ('Após prazo' if previsto else 'Sem data prevista')})
    recentes.sort(key=lambda x:(x['entregue'],x['numero']),reverse=True)
    ativos=[(numero,p) for numero,p in pedidos if not status_bool(p,'entregue') and status_bool(p,'aprovado') and not status_bool(p,'cancelado_cliente')]
    vencidos=sum(1 for _,p in ativos if (d:=_data(p.get('data_entrega'))) and d<hoje)
    proximos=sum(1 for _,p in ativos if (d:=_data(p.get('data_entrega'))) and hoje<=d<=hoje+timedelta(days=2))
    sem_prazo=sum(1 for _,p in ativos if not _data(p.get('data_entrega')))
    return {'dias':dias,'periodo_inicio':inicio,'periodo_fim':hoje,'prontos':prontas,'prontos_anterior':prontas_ant,'entregues':entregues,'entregues_anterior':entregues_ant,'entregas_com_prazo':len(avaliaveis),'entregas_no_prazo':sum(avaliaveis),'mediana_dias_aprovacao_entrega':median(duracoes) if duracoes else None,'duracoes_validas':len(duracoes),'abertos_aprovados':len(ativos),'vencidos':vencidos,'proximos_2_dias':proximos,'sem_prazo':sem_prazo,'recentes':recentes[:12]}
