"""Consolidação leve de resultados comerciais/financeiros.

HF48: preserva exatamente as listas e a ordem de soma do cálculo homologado,
mas calcula o valor de cada proposta uma única vez e reaproveita o resultado.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Callable, Iterable


def calcular_resultados_runtime(
    historico: Iterable[dict[str, Any]] | None,
    referencia: date,
    *,
    proposta_encerrada: Callable[[dict[str, Any]], bool],
    proposta_faturamento_mensal: Callable[[dict[str, Any]], bool],
    valor_bool: Callable[[Any], bool],
    total_proposta: Callable[[dict[str, Any]], float],
    data_evento: Callable[[dict[str, Any], tuple[str, ...]], tuple[date | None, str, bool]],
) -> dict[str, Any]:
    propostas = [p for p in (historico or []) if isinstance(p, dict)]
    inicio_mes = referencia.replace(day=1)

    # HF48: custo mais caro do painel comercial calculado só uma vez/proposta.
    totais_por_objeto = {id(p): total_proposta(p) for p in propostas}
    def total_lista(lista):
        # Mantém a mesma ordem e o mesmo `sum()` do cálculo anterior.
        return sum(totais_por_objeto[id(p)] for p in lista)

    validas = []
    aprovadas = []
    pagas = []
    a_receber = []
    mensais_a_faturar = []
    criadas_hoje = []
    aprovadas_hoje = []
    pagas_hoje = []
    entregues_hoje = []
    propostas_mes = []
    aprovadas_mes = []
    fallback_eventos = {"aprovacao": 0, "pagamento": 0, "entrega": 0}

    # Uma passagem principal preservando a ordem original das listas.
    for p in propostas:
        d_criacao, _, _ = data_evento(p, ("data_geracao", "data", "criado_em", "created_at"))
        if d_criacao == referencia:
            criadas_hoje.append(p)
        if d_criacao and inicio_mes <= d_criacao <= referencia:
            propostas_mes.append(p)

        if proposta_encerrada(p):
            continue
        validas.append(p)

        aprovado = valor_bool(p.get("aprovado"))
        pago = valor_bool(p.get("pago"))
        entregue = valor_bool(p.get("entregue"))

        if aprovado:
            aprovadas.append(p)
            d_aprovacao, _, _ = data_evento(p, ("aprovado_em", "data_aprovacao"))
            if d_aprovacao == referencia:
                aprovadas_hoje.append(p)
            if d_aprovacao is None:
                fallback_eventos["aprovacao"] += 1

            mensal = proposta_faturamento_mensal(p)
            if not pago:
                if mensal:
                    mensais_a_faturar.append(p)
                else:
                    a_receber.append(p)

        if pago:
            pagas.append(p)
            d_pagamento, _, _ = data_evento(p, ("pago_em", "data_pagamento"))
            if d_pagamento == referencia:
                pagas_hoje.append(p)
            if d_pagamento is None:
                fallback_eventos["pagamento"] += 1

        if entregue:
            d_entrega, _, _ = data_evento(p, ("entregue_em", "data_entrega_real"))
            if d_entrega == referencia:
                entregues_hoje.append(p)
            if d_entrega is None:
                fallback_eventos["entrega"] += 1

    # A lógica anterior reavaliava encerramento para as propostas do mês. Isso é
    # mantido por compatibilidade, mas o valor financeiro já está em cache.
    aprovadas_mes = [
        p for p in propostas_mes
        if (not proposta_encerrada(p)) and valor_bool(p.get("aprovado"))
    ]

    total_orcado = total_lista(propostas)
    total_aprovadas_mes = total_lista(aprovadas_mes)
    return {
        "referencia": referencia,
        "propostas_total": len(propostas),
        "propostas_validas": len(validas),
        "propostas_encerradas": len(propostas) - len(validas),
        "aprovadas_total": len(aprovadas),
        "pagas_total": len(pagas),
        "a_receber_total_qtd": len(a_receber),
        "mensais_a_faturar_qtd": len(mensais_a_faturar),
        "total_orcado": total_orcado,
        "total_orcado_valido": total_lista(validas),
        "total_aprovado": total_lista(aprovadas),
        "total_recebido": total_lista(pagas),
        "a_receber": total_lista(a_receber),
        "mensais_a_faturar": total_lista(mensais_a_faturar),
        "orcado_hoje": total_lista(criadas_hoje),
        "confirmado_hoje": total_lista(aprovadas_hoje),
        "recebido_hoje": total_lista(pagas_hoje),
        "entregues_hoje": len(entregues_hoje),
        "propostas_mes": propostas_mes,
        "aprovadas_mes": aprovadas_mes,
        "total_mes": total_lista(propostas_mes),
        "confirmado_mes": total_aprovadas_mes,
        "ticket_medio": (total_orcado / len(propostas)) if propostas else 0.0,
        "ticket_aprovado_mes": (total_aprovadas_mes / len(aprovadas_mes)) if aprovadas_mes else 0.0,
        "conversao_mes": (len(aprovadas_mes) / len(propostas_mes) * 100.0) if propostas_mes else 0.0,
        "fallback_eventos": fallback_eventos,
        "_listas": {
            "propostas": propostas,
            "validas": validas,
            "aprovadas": aprovadas,
            "pagas": pagas,
            "a_receber": a_receber,
            "mensais_a_faturar": mensais_a_faturar,
            "criadas_hoje": criadas_hoje,
            "aprovadas_hoje": aprovadas_hoje,
            "pagas_hoje": pagas_hoje,
            "entregues_hoje": entregues_hoje,
        },
    }
