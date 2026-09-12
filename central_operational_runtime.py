"""Snapshot operacional compartilhado da Central AlphaFest.

HF36 — consolida, em uma única fotografia somente leitura, os cálculos que
antes eram repetidos no mesmo rerun da Central: previsão de produção, fila de
saída, central de produção e prioridades operacionais.

Nenhum status é persistido por este módulo. As fontes oficiais continuam sendo
Histórico, consumo/reservas, estoque, planejamento de compras e Fluxo.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Callable, Iterable

from risco_producao_engine import montar_previsao_producao
from central_producao_engine import montar_central_producao, resumo_central
from central_entregas_engine import montar_fila, resumo_fila
from prioridade_operacional_engine import (
    montar_prioridades_operacionais,
    resumo_prioridades,
    indexar_prioridades,
)


def montar_snapshot_operacional(
    propostas: Iterable[dict] | None,
    tarefas_ativas: Iterable[dict] | None,
    consumos: Iterable[dict] | None,
    estoque: dict[str, Any] | None,
    planejamentos: Iterable[dict] | None,
    hoje: date,
    *,
    resumo_produtos: Callable[[dict], str] | None = None,
) -> dict[str, Any]:
    """Monta uma fotografia coerente e reaproveitável da operação.

    A função mantém as mesmas engines já homologadas. O ganho vem apenas de
    executar cada derivação uma vez e compartilhar o resultado entre os blocos
    da Central no mesmo rerun.
    """
    propostas_l = list(propostas or [])
    tarefas_l = list(tarefas_ativas or [])
    consumos_l = list(consumos or [])
    planejamentos_l = list(planejamentos or [])
    estoque_d = estoque if isinstance(estoque, dict) else {}
    movimentos = list(estoque_d.get("movimentacoes") or [])

    fila_entregas = montar_fila(
        propostas_l,
        hoje,
        resumo_produtos=resumo_produtos,
    )
    previsao = montar_previsao_producao(
        propostas_l,
        consumos_l,
        movimentos,
        planejamentos_l,
        hoje=hoje,
    )
    central_producao = montar_central_producao(
        previsao,
        tarefas_l,
        hoje=hoje,
    )
    prioridades = montar_prioridades_operacionais(
        propostas_l,
        hoje,
        central_producao=central_producao,
        fila_entregas=fila_entregas,
        resumo_produtos=resumo_produtos,
    )

    return {
        "previsao": previsao,
        "central_producao": central_producao,
        "resumo_central_producao": resumo_central(central_producao),
        "fila_entregas": fila_entregas,
        "resumo_fila_entregas": resumo_fila(fila_entregas),
        "prioridades": prioridades,
        "resumo_prioridades": resumo_prioridades(prioridades),
        "mapa_prioridades": indexar_prioridades(prioridades),
    }
