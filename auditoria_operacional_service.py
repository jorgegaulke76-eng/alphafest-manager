"""20.4.9-I8.13.5-HF2 — serviço modular de auditoria e sincronização operacional.

Este módulo não depende de Streamlit nem do Supabase. A camada de aplicação injeta
as funções de leitura/gravação necessárias. Assim, a regra de auditoria pode ser
testada isoladamente e usada por qualquer tela sem criar uma segunda verdade.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Iterable

from consistencia_operacional_engine import auditar_consistencia_operacional


def executar_auditoria_sincronizacao(
    *,
    historico: list[dict[str, Any]],
    tarefas_antes: list[dict[str, Any]],
    consumos: Any,
    estoque: Any,
    planejamentos: Any,
    hoje: Any,
    momento: str,
    montar_previsao: Callable[..., list[dict[str, Any]]],
    montar_fila_entregas: Callable[..., list[dict[str, Any]]],
    reconciliar_fluxo: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
    resumo_produtos: Callable[[dict[str, Any]], str] | None = None,
) -> dict[str, Any]:
    """Executa a comparação operacional e o único reparo automático permitido.

    A Fonte Única continua sendo ``historico``. O único reparo persistente que
    esta rotina solicita é a reconciliação do espelho do Fluxo via callback.
    Risco e Entregas são sempre projeções derivadas.
    """
    previsao = montar_previsao(
        historico=historico,
        consumos=consumos,
        estoque=estoque,
        planejamentos=planejamentos,
    )
    fila = montar_fila_entregas(historico, hoje, resumo_produtos=resumo_produtos)

    rel_antes = auditar_consistencia_operacional(historico, tarefas_antes, previsao, fila)
    tarefas_depois = reconciliar_fluxo(historico)
    rel_depois = auditar_consistencia_operacional(historico, tarefas_depois, previsao, fila)

    reparos = max(0, int(rel_antes.get("problemas", 0)) - int(rel_depois.get("problemas", 0)))
    relatorio = deepcopy(rel_depois)
    relatorio["problemas_antes"] = int(rel_antes.get("problemas", 0))
    relatorio["reparos_automaticos"] = reparos
    relatorio["momento"] = str(momento)
    return relatorio


def contexto_auditoria_sincronizacao(relatorio: dict[str, Any] | None) -> dict[str, Any]:
    """Monta o payload padronizado para registrar a auditoria oficial."""
    relatorio = relatorio or {}
    return {
        "origem": "Auditoria de Sincronização HF6",
        "problemas_antes": int(relatorio.get("problemas_antes", 0) or 0),
        "problemas_depois": int(relatorio.get("problemas", 0) or 0),
        "reparos_automaticos": int(relatorio.get("reparos_automaticos", 0) or 0),
        "fluxo_faltantes": list(relatorio.get("fluxo_faltantes") or [])[:20],
        "risco_indevido": list(relatorio.get("risco_indevido") or [])[:20],
        "previsao_indevida": list(relatorio.get("previsao_indevida") or [])[:20],
        "saida_indevida": list(relatorio.get("saida_indevida") or [])[:20],
        "contradicoes": list(relatorio.get("contradicoes") or [])[:20],
    }


def aplicar_plano_saneamento(
    *,
    plano_inicial: dict[str, Any] | None,
    atualizar_proposta: Callable[[str, Callable[[dict[str, Any]], None]], tuple[bool, Any, str]],
    aplicar_correcoes: Callable[[dict[str, Any]], list[dict[str, Any]]],
    registrar_mudanca: Callable[..., Any],
    origem: str = "Saneamento Histórico HF7",
) -> dict[str, Any]:
    """Aplica um plano previamente calculado, uma proposta por vez.

    O callback ``atualizar_proposta`` é responsável pela leitura fresca/CAS. Uma
    mudança só é auditada depois de a atualização retornar sucesso.
    """
    plano_inicial = plano_inicial or {}
    resultados: list[dict[str, Any]] = []
    falhas: list[dict[str, Any]] = []
    total_aplicado = 0

    for plano in plano_inicial.get("planos", []) or []:
        numero = str((plano or {}).get("pedido") or "").strip()
        if not numero:
            continue
        aplicadas: list[dict[str, Any]] = []

        def _mutar(proposta: dict[str, Any]) -> None:
            aplicadas.clear()
            aplicadas.extend(aplicar_correcoes(proposta))

        ok, _atualizada, motivo = atualizar_proposta(numero, _mutar)
        if not ok:
            falhas.append({"pedido": numero, "motivo": str(motivo or "Falha de gravação")})
            continue

        for correcao in list(aplicadas):
            campo = str(correcao.get("campo") or "")
            registrar_mudanca(
                "Proposta",
                numero,
                f"status.{campo}",
                correcao.get("valor_anterior"),
                correcao.get("valor_novo"),
                origem=origem,
                contexto={
                    "motivo": correcao.get("motivo"),
                    "saneamento_seguro": True,
                    "sem_inferencia_pagamento": True,
                },
            )
            resultados.append({
                "Pedido": numero,
                "Campo": f"status.{campo}",
                "Mudança": "NÃO → SIM",
                "Motivo": correcao.get("motivo"),
                "Resultado": "OK",
            })
            total_aplicado += 1

    return {
        "alteracoes_confirmadas": total_aplicado,
        "resultados": resultados,
        "falhas": falhas,
    }


def linhas_previa_saneamento(plano: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Converte a prévia em linhas de apresentação, sem conhecer pandas/Streamlit."""
    linhas: list[dict[str, Any]] = []
    for item in (plano or {}).get("planos", []) or []:
        for correcao in (item or {}).get("correcoes", []) or []:
            linhas.append({
                "Pedido": item.get("pedido"),
                "Cliente": item.get("cliente"),
                "Campo": f"status.{correcao.get('campo')}",
                "Atual": "NÃO",
                "Novo": "SIM",
                "Motivo": correcao.get("motivo"),
            })
    return linhas


def linhas_relatorio_sincronizacao(relatorio: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Converte divergências em linhas únicas para qualquer interface."""
    relatorio = relatorio or {}
    grupos = [
        ("Pedidos ativos sem Fluxo", relatorio.get("fluxo_faltantes") or []),
        ("Fluxo ativo para pedido já encerrado", relatorio.get("fluxo_fechados_ativos") or []),
        ("Fluxo órfão", relatorio.get("fluxo_orfaos") or []),
        ("Previsão ausente", relatorio.get("previsao_faltantes") or []),
        ("Previsão indevida", relatorio.get("previsao_indevida") or []),
        ("Risco indevido", relatorio.get("risco_indevido") or []),
        ("Pronto ausente em Entregas", relatorio.get("saida_faltantes") or []),
        ("Entrega indevida", relatorio.get("saida_indevida") or []),
    ]
    linhas: list[dict[str, Any]] = []
    for tipo, numeros in grupos:
        for numero in list(numeros)[:50]:
            linhas.append({"Tipo": tipo, "Pedido": numero})
    for contradicao in relatorio.get("contradicoes") or []:
        linhas.append({
            "Tipo": "Status contraditório",
            "Pedido": (contradicao or {}).get("pedido"),
            "Detalhe": (contradicao or {}).get("problema"),
        })
    return linhas
