"""Briefing executivo do THU para o perfil de gestão.

Módulo somente leitura: transforma dados operacionais em um resumo curto sem
alterar a Central da Anna ou os documentos comerciais.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable

import streamlit as st

from alpha_core import listar_atrasados_operacionais
from proposal_status import status_bool as _status_bool, proposta_pronta as _status_pronta


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value or "").strip().casefold() in {"1", "true", "sim", "yes", "ok", "pago", "aprovado", "pronto", "entregue"}


def _data(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    texto = str(value or "").strip()
    if not texto:
        return None
    for candidato in (texto, texto[:19], texto[:10]):
        for formato in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(candidato, formato).date()
            except (TypeError, ValueError):
                pass
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")).date()
    except (TypeError, ValueError):
        return None


def _valor_total(proposta: dict[str, Any], calculadora: Callable[[dict[str, Any]], tuple[Any, Any, Any]] | None) -> float:
    if calculadora is not None:
        try:
            return float(calculadora(proposta)[2] or 0)
        except Exception:
            pass
    for campo in ("valor_total", "total", "valor", "total_geral"):
        try:
            return float(str(proposta.get(campo, 0)).replace("R$", "").replace(".", "").replace(",", ".").strip() or 0)
        except (TypeError, ValueError):
            continue
    return 0.0


def calcular_briefing(
    historico: list[dict[str, Any]],
    indicadores: dict[str, Any],
    hoje: date,
    calcular_valores: Callable[[dict[str, Any]], tuple[Any, Any, Any]] | None = None,
) -> dict[str, Any]:
    propostas = list(historico or [])
    pagos_hoje = [
        p for p in propostas
        if _status_bool(p, "pago") and _data(p.get("pago_em") or p.get("data_pagamento") or p.get("atualizado_em")) == hoje
    ]
    recebido_hoje = sum(_valor_total(p, calcular_valores) for p in pagos_hoje)

    aprovados_abertos = [p for p in propostas if _status_bool(p, "aprovado") and not _status_bool(p, "entregue")]
    previsto_aberto = sum(_valor_total(p, calcular_valores) for p in aprovados_abertos)

    entregas_hoje = [p for p in aprovados_abertos if _data(p.get("data_entrega")) == hoje]
    prontos_aguardando = [p for p in aprovados_abertos if _status_pronta(p)]
    # HF2: não recalcular atraso com regra própria. O THU consome a lista
    # oficial do Alpha Core para garantir os mesmos pedidos e a mesma contagem.
    atrasados = listar_atrasados_operacionais(propostas, hoje)

    alertas: list[str] = []
    if atrasados:
        alertas.append(f"{len(atrasados)} pedido(s) com prazo vencido")
    if indicadores.get("aguardando_aprovacao", 0):
        alertas.append(f"{indicadores['aguardando_aprovacao']} orçamento(s) aguardando aprovação")
    if indicadores.get("pagamentos_pendentes", 0):
        alertas.append(f"{indicadores['pagamentos_pendentes']} pagamento(s) pendente(s)")
    if not alertas:
        alertas.append("Operação sem alertas críticos neste momento")

    return {
        "recebido_hoje": recebido_hoje,
        "previsto_aberto": previsto_aberto,
        "entregas_hoje": len(entregas_hoje),
        "prontos_aguardando_entrega": len(prontos_aguardando),
        "atrasados": len(atrasados),
        "pedidos_ativos": int(indicadores.get("pedidos_ativos", indicadores.get("propostas_abertas", 0))),
        "aguardando_aprovacao": int(indicadores.get("aguardando_aprovacao", 0)),
        "pagamentos_pendentes": int(indicadores.get("pagamentos_pendentes", 0)),
        "propostas_hoje": int(indicadores.get("propostas_hoje", 0)),
        "alertas": alertas,
    }


def renderizar_briefing_thu(nome: str, briefing: dict[str, Any]) -> None:
    saudacao = "Bom dia" if datetime.now().hour < 12 else ("Boa tarde" if datetime.now().hour < 18 else "Boa noite")
    st.markdown("### 🐵 THU — prioridades agora")

    tarefas: list[tuple[str, str]] = []
    if briefing.get("atrasados", 0):
        tarefas.append(("🔴", f"Resolver {briefing['atrasados']} pedido(s) atrasado(s) primeiro"))
    if briefing.get("prontos_aguardando_entrega", 0):
        tarefas.append(("📦", f"Acompanhar {briefing['prontos_aguardando_entrega']} pedido(s) pronto(s) aguardando retirada/entrega"))
    if briefing.get("entregas_hoje", 0):
        tarefas.append(("🚚", f"Conferir {briefing['entregas_hoje']} entrega(s) prevista(s) para hoje"))
    if briefing.get("aguardando_aprovacao", 0):
        tarefas.append(("🟡", f"Retomar {briefing['aguardando_aprovacao']} orçamento(s) aguardando aprovação"))
    if briefing.get("pagamentos_pendentes", 0):
        tarefas.append(("💰", f"Conferir {briefing['pagamentos_pendentes']} pagamento(s) pendente(s)"))
    if not tarefas:
        tarefas.append(("🟢", "Operação sem pendências críticas neste momento"))

    lista = "".join(
        f'<div style="padding:6px 0;border-bottom:1px solid #dbeafe;"><b>{icone}</b> {texto}</div>'
        for icone, texto in tarefas[:4]
    )
    st.markdown(
        f'<div style="border:1px solid #b7d7ff;border-left:7px solid #0969da;border-radius:16px;padding:13px 16px;background:linear-gradient(135deg,#f7fbff,#eef7ff);margin-bottom:10px;">'
        f'<div style="font-size:1.05rem;font-weight:800;color:#0b3a68;">{saudacao}, {nome}. Este é o melhor caminho agora:</div>'
        f'<div style="color:#36566f;margin-top:7px;">{lista}</div></div>',
        unsafe_allow_html=True,
    )

    recebido = f"R$ {briefing.get('recebido_hoje', 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    valores = [
        ("📄", "Orçamentos hoje", briefing.get("propostas_hoje", 0)),
        ("📦", "Pedidos ativos", briefing.get("pedidos_ativos", 0)),
        ("✅", "Prontos", briefing.get("prontos_aguardando_entrega", 0)),
        ("🚚", "Entregas hoje", briefing.get("entregas_hoje", 0)),
        ("💵", "Recebido hoje", recebido),
        ("🟡", "Aprovação", briefing.get("aguardando_aprovacao", 0)),
        ("🔴", "Atrasados", briefing.get("atrasados", 0)),
    ]
    cols = st.columns(7)
    for col, (icone, rotulo, valor) in zip(cols, valores):
        col.markdown(
            f'<div style="border:1px solid #263244;border-radius:12px;padding:9px 8px;text-align:center;min-height:78px;">'
            f'<div style="font-size:.78rem;opacity:.78;">{icone} {rotulo}</div>'
            f'<div style="font-size:1.35rem;font-weight:800;margin-top:5px;">{valor}</div></div>',
            unsafe_allow_html=True,
        )

