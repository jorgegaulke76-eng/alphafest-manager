"""HF65.24.53 — formulário privado de HOMOLOGAÇÃO sem persistência.

Uso futuro: render_private_attribution_preview(st, propostas, atendimentos, eventos,
usuario). Nunca chamá-lo no site público nem sem controle de acesso.
O botão prepara um evento validado para revisão, mas NÃO grava banco.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from commercial_attribution_service import (
    build_attribution_event, effective_attributions,
)


def render_private_attribution_preview(
    st: Any,
    propostas: Iterable[Mapping[str, Any]],
    atendimentos: Iterable[Mapping[str, Any]],
    eventos: Iterable[Mapping[str, Any]],
    *,
    usuario: str,
) -> dict[str, str] | None:
    """Somente prévia explícita. Persistência requer adapter e autorização separados."""
    orders = [p for p in propostas if isinstance(p, Mapping)]
    contacts = [c for c in atendimentos if isinstance(c, Mapping)]
    current = effective_attributions(eventos)
    st.subheader("HF65.24.53 · Vincular campanha (prévia sem gravação)")
    st.caption(
        "Ação assistida. Não altera proposta, atendimento, Supabase nem faturamento. "
        "Clique no WhatsApp não representa mensagem recebida ou venda."
    )
    available = sorted({
        str(p.get("numero_proposta") or "").strip() for p in orders
        if str(p.get("numero_proposta") or "").strip()
    })
    if not available:
        st.info("Nenhuma proposta oficial disponível para vinculação.")
        return None
    with st.form("hf65_24_53_link_preview"):
        number = st.selectbox("Proposta oficial", available)
        matching = [p for p in orders
                    if str(p.get("numero_proposta") or "").strip() == number]
        aid = str(matching[0].get("atendimento_id") or "").strip() if len(matching) == 1 else ""
        st.text_input("Atendimento associado", value=aid, disabled=True)
        campaign = st.text_input("Referência da campanha", max_chars=120,
                                 placeholder="instagram_natal_2026")
        evidence = st.selectbox("Evidência conferida no atendimento", [
            "mensagem_whatsapp", "referencia_cliente",
            "link_utm_conferido", "atendimento_manual",
        ])
        decision = st.radio("Ação", ["confirmar", "revogar"], horizontal=True)
        st.caption("Revisão de vínculo existente: " +
                   (next((v["campaign"] for v in current
                          if v["numero_proposta"] == number), "Sem campanha confirmada")))
        submitted = st.form_submit_button("Validar prévia (não salvar)")
    if not submitted:
        return None
    try:
        event = build_attribution_event(
            numero_proposta=number,
            atendimento_id=aid,
            campaign=campaign,
            decisao=decision,
            evidencia=evidence,
            usuario=usuario,
            ocorrido_em=datetime.now(timezone.utc).isoformat(),
            propostas=orders,
            atendimentos=contacts,
        )
    except ValueError as exc:
        st.error(str(exc))
        return None
    st.success("Evento validado localmente. Nada foi gravado.")
    st.json(event)
    return event
