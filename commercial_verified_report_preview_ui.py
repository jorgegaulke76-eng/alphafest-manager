"""HF65.24.53 — visualização privada de homologação, somente leitura.

Não é montada automaticamente no Manager, não consulta dados ou credenciais.
O aplicativo anfitrião deverá autenticar/autorizar o operador antes de chamar.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable, Mapping

from commercial_verified_report import build_verified_commercial_report


def render_verified_report_preview(
    st: Any,
    *,
    atendimentos: Iterable[Mapping[str, Any]],
    propostas: Iterable[Mapping[str, Any]],
    eventos_auditados: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Mostra somente agregados; não imprime PII ou eventos brutos."""
    report = build_verified_commercial_report(
        atendimentos, propostas, eventos_auditados
    )
    st.subheader("HF65.24.53 · Campanhas e pagamentos (homologação)")
    st.warning(
        "Prévia sem acesso à produção. Dados fornecidos pelo operador; "
        "não é relatório financeiro oficial e não comprova envio de WhatsApp."
    )
    a, b, c = st.columns(3)
    a.metric("Atendimentos únicos", report["contatos_unicos"])
    b.metric("Pedidos pagos atribuídos", report["pedidos_pagos_atribuidos"])
    c.metric("Receita atribuída (experimental)",
             f"R$ {report['receita_atribuida']:,.2f}".replace(",", "X")
             .replace(".", ",").replace("X", "."))
    rows = [
        {
            "Campanha": x["campanha"],
            "Pedidos pagos": x["pedidos_pagos_atribuidos"],
            "Receita atribuída (R$)": float(x["receita_atribuida"]),
        }
        for x in report["campanhas"]
    ]
    if rows:
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        st.info("Nenhum pedido pago com campanha inequivocamente confirmada.")
    st.caption(report["aviso"])
    return report
