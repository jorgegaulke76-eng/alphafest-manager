"""Briefing executivo do THU para o perfil de gestão.

Módulo somente leitura: transforma dados operacionais em um resumo curto sem
alterar a Central da Anna ou os documentos comerciais.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable

import streamlit as st


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value or "").strip().casefold() in {"1", "true", "sim", "yes", "ok", "pago", "aprovado", "entregue"}


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
        if _bool(p.get("pago")) and _data(p.get("pago_em") or p.get("data_pagamento") or p.get("atualizado_em")) == hoje
    ]
    recebido_hoje = sum(_valor_total(p, calcular_valores) for p in pagos_hoje)

    aprovados_abertos = [p for p in propostas if _bool(p.get("aprovado")) and not _bool(p.get("entregue"))]
    previsto_aberto = sum(_valor_total(p, calcular_valores) for p in aprovados_abertos)

    entregas_hoje = [p for p in aprovados_abertos if _data(p.get("data_entrega")) == hoje]
    atrasados = [p for p in aprovados_abertos if (_data(p.get("data_entrega")) or date.max) < hoje]

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
        "atrasados": len(atrasados),
        "pedidos_ativos": int(indicadores.get("pedidos_ativos", indicadores.get("propostas_abertas", 0))),
        "aguardando_aprovacao": int(indicadores.get("aguardando_aprovacao", 0)),
        "propostas_hoje": int(indicadores.get("propostas_hoje", 0)),
        "alertas": alertas,
    }


def renderizar_briefing_thu(nome: str, briefing: dict[str, Any]) -> None:
    saudacao = "Bom dia" if datetime.now().hour < 12 else ("Boa tarde" if datetime.now().hour < 18 else "Boa noite")
    st.markdown("### 🐵 Briefing do THU")
    st.markdown(
        f"""
        <div style="border:1px solid #b7d7ff;border-left:7px solid #0969da;border-radius:16px;padding:16px 18px;background:linear-gradient(135deg,#f7fbff,#eef7ff);margin-bottom:12px;">
          <div style="font-size:1.08rem;font-weight:800;color:#0b3a68;">{saudacao}, {nome}!</div>
          <div style="color:#36566f;margin-top:4px;">Preparei um resumo objetivo da operação para você começar pelas prioridades.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📄 Orçamentos hoje", briefing["propostas_hoje"])
    c2.metric("📦 Pedidos ativos", briefing["pedidos_ativos"])
    c3.metric("🚚 Entregas hoje", briefing["entregas_hoje"])
    c4.metric("💵 Recebido hoje", f"R$ {briefing['recebido_hoje']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    a1, a2, a3 = st.columns(3)
    a1.metric("🟡 Aguardando aprovação", briefing["aguardando_aprovacao"])
    a2.metric("🔴 Atrasados", briefing["atrasados"])
    a3.metric("💰 Carteira aprovada aberta", f"R$ {briefing['previsto_aberto']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    cor = "#fff7ed" if briefing["atrasados"] else "#f0fdf4"
    borda = "#ea580c" if briefing["atrasados"] else "#16a34a"
    itens = "".join(f"<li>{item}</li>" for item in briefing["alertas"])
    st.markdown(
        f'<div style="background:{cor};border-left:6px solid {borda};border-radius:12px;padding:12px 16px;"><b>🎯 THU recomenda atenção em:</b><ul style="margin-bottom:0;">{itens}</ul></div>',
        unsafe_allow_html=True,
    )
