"""HF65.24.48 — planejamento leve, exclusivamente de leitura.

Usa a mesma fila da Central de Produção. Um pedido não é duplicado entre
vencidos, semana e sem prazo. Não cria compromissos nem modifica status.
"""
from __future__ import annotations
from datetime import date, timedelta


def planejar(fila, hoje: date | None = None, dias: int = 7):
    hoje = hoje or date.today()
    if not 1 <= dias <= 31:
        raise ValueError('dias fora da faixa permitida')
    fim = hoje + timedelta(days=dias - 1)
    calendario = [{'data': hoje + timedelta(days=i), 'pedidos': [], 'total': 0}
                  for i in range(dias)]
    por_data = {d['data']: d for d in calendario}
    vencidos, sem_data, fora_periodo = [], [], []
    vistos = set()
    for item in fila or []:
        if not isinstance(item, dict):
            continue
        numero = str(item.get('numero_proposta') or '').strip()
        # Pedidos sem identificação não devem desaparecer, mas não colapsamos
        # dois registros diferentes só porque ambos não têm número.
        chave = ('numero', numero) if numero else ('anonimo', id(item))
        if chave in vistos:
            continue
        vistos.add(chave)
        entrega = item.get('entrega_hf41')
        if isinstance(entrega, str):
            try: entrega = date.fromisoformat(entrega)
            except ValueError: entrega = None
        if entrega is None:
            sem_data.append(item)
        elif entrega < hoje:
            vencidos.append(item)
        elif entrega <= fim:
            por_data[entrega]['pedidos'].append(item)
        else:
            fora_periodo.append(item)
    for d in calendario:
        d['pedidos'].sort(key=lambda p: (str(p.get('numero_proposta') or ''), str(p.get('cliente_nome') or '')))
        d['total'] = len(d['pedidos'])
    vencidos.sort(key=lambda p: (p.get('entrega_hf41') or date.max, str(p.get('numero_proposta') or '')))
    return {
        'inicio': hoje, 'fim': fim, 'dias': calendario,
        'total_semana': sum(d['total'] for d in calendario),
        'dias_com_entregas': sum(d['total'] > 0 for d in calendario),
        'pico': max((d['total'] for d in calendario), default=0),
        'vencidos': vencidos, 'sem_data': sem_data,
        'fora_periodo': fora_periodo,
    }
