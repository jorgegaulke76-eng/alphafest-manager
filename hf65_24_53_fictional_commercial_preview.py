"""Prévia COMERCIAL inteiramente fictícia para homologação visual da HF65.24.53.

Todos os atendimentos, pedidos, campanhas e contagens de WhatsApp são
fabricados para demonstração. Nunca consulta arquivos, Supabase, Manager,
analytics ou credenciais; não cria eventos e não habilita o relatório real.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from commercial_verified_report import build_verified_commercial_report


def fictional_commercial_scenario() -> dict[str, Any]:
    contacts = [
        {"id": f"EX-AT-{i}", "etapa_captacao": "Venda fechada" if i <= 3 else "Novo contato"}
        for i in range(1, 9)
    ]
    proposals = [
        {"numero_proposta":"EX-P1", "atendimento_id":"EX-AT-1", "pago":True, "valor_total":"120,00"},
        {"numero_proposta":"EX-P2", "atendimento_id":"EX-AT-2", "pago":True, "valor_total":"80,00"},
        {"numero_proposta":"EX-P3", "atendimento_id":"EX-AT-3", "pago":True, "valor_total":"200,00", "valor_recebido":"90,00"},
        {"numero_proposta":"EX-P4", "atendimento_id":"EX-AT-4", "pago":True, "valor_total":"300,00", "modalidade_cobranca":"Mensalista"},
        {"numero_proposta":"EX-P5", "atendimento_id":"EX-AT-5", "pago":True, "valor_total":"150,00", "cancelado_cliente":True},
        {"numero_proposta":"EX-P6", "atendimento_id":"EX-AT-6", "pago":True, "valor_total":"90,00", "valor_estornado":"90,00"},
        {"numero_proposta":"EX-P7", "atendimento_id":"EX-AT-7", "pago":False, "valor_total":"60,00"},
        {"numero_proposta":"EX-P8", "atendimento_id":"EX-AT-8", "pago":True, "valor_total":"70,00"},
    ]
    campaigns = ["natal_2026", "instagram", "natal_2026", "instagram",
                 "natal_2026", "instagram", "natal_2026", "natal_2026"]
    def event(i: int, decision: str, minute: int) -> dict[str, str]:
        return {
            "numero_proposta": f"EX-P{i}", "atendimento_id": f"EX-AT-{i}",
            "campaign": campaigns[i-1], "decisao": decision,
            "evidencia": "referencia_cliente", "usuario": "operador_ficticio",
            "ocorrido_em": f"2026-11-24T10:{minute:02d}:00-03:00",
        }
    before_events = [event(i, "confirmar", 0) for i in range(1, 9)]
    after_events = before_events + [event(8, "revogar", 1)]
    return {
        "before": build_verified_commercial_report(contacts, proposals, before_events),
        "after": build_verified_commercial_report(contacts, proposals, after_events),
        "whatsapp_clicks_fictional": 42,
        "scenarios": [
            ("Clique no WhatsApp", "Interesse; não demonstra orçamento enviado nem venda"),
            ("Proposta com marcador pago", "Valor comercial operacional, não extrato bancário"),
            ("Pagamento parcial", "Excluído do valor comercial atribuído até conciliação"),
            ("Mensalista", "Excluído; fechamento financeiro é separado"),
            ("Cancelamento ou estorno", "Não contabilizado"),
            ("Vínculo de campanha revogado", "Retira a atribuição sem apagar o histórico"),
        ],
    }


def _brl(value: Decimal) -> str:
    return "R$ " + f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render_fictional_commercial_preview(st: Any) -> None:
    """Prévia sem entrada de usuário e sem qualquer chamada de rede."""
    st.subheader("HF65.24.53 — Aceite comercial (dados fictícios)")
    st.warning(
        "DEMONSTRAÇÃO FICTÍCIA: nenhum dado real, clique real, orçamento, "
        "pedido ou recebimento bancário foi consultado."
    )
    try:
        demo = fictional_commercial_scenario()
        before, after = demo["before"], demo["after"]
        a,b,c = st.columns(3)
        a.metric("Cliques WhatsApp fictícios", demo["whatsapp_clicks_fictional"])
        b.metric("Pedidos atribuídos após revogação", after["pedidos_pagos_atribuidos"])
        c.metric("Valor comercial atribuído", _brl(after["receita_atribuida"]))
        st.caption(
            "Exemplo: antes da revogação, "
            + _brl(before["receita_atribuida"])
            + "; após a revogação, "
            + _brl(after["receita_atribuida"])
            + ". Nenhum clique foi convertido automaticamente em venda."
        )
        st.dataframe([
            {
                "Campanha fictícia": row["campanha"],
                "Pedidos atribuídos": row["pedidos_pagos_atribuidos"],
                "Valor comercial (não bancário)": _brl(row["receita_atribuida"]),
            }
            for row in after["campanhas"]
        ], hide_index=True, use_container_width=True)
        st.caption("Regras exemplificadas: " + "; ".join(
            f"{name}: {meaning}" for name, meaning in demo["scenarios"]
        ))
        st.caption(after["aviso"])
        st.info("Somente prévia para aceite visual. Relatório privado continua desligado.")
    except Exception:
        st.error("Demonstração indisponível. Nenhum relatório privado foi aberto.")
