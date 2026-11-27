"""Centro Executivo do Jorge — leitura segura do Alpha Core."""
from __future__ import annotations

from typing import Any
import streamlit as st


def _money(value: float) -> str:
    return f"R$ {float(value or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def renderizar_centro_executivo(snapshot: Any, indicadores_legados: dict[str, Any] | None = None) -> None:
    dados = snapshot.to_dict() if hasattr(snapshot, "to_dict") else dict(snapshot or {})
    st.markdown("### 🧠 Alpha Core — Empresa Agora")
    status = str(dados.get("qualidade") or "Saudável")
    cor = {"Saudável": "#16a34a", "Atenção": "#d97706", "Crítico": "#dc2626"}.get(status, "#0969da")
    st.markdown(
        f'<div style="border-left:7px solid {cor};background:#f8fafc;border-radius:14px;padding:12px 16px;margin-bottom:12px;">'
        f'<b style="color:{cor};">● Empresa {status}</b><br><span style="color:#475569;">Fonte única de leitura para o perfil executivo e o THU.</span></div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📦 Pedidos ativos", dados.get("pedidos_ativos", 0))
    c2.metric("🟡 Aprovação", dados.get("aguardando_aprovacao", 0))
    c3.metric("✅ Prontos", dados.get("prontos_aguardando_entrega", 0), help="Produção concluída; aguardando retirada/entrega.")
    c4.metric("🚚 Pendentes hoje", dados.get("pendentes_entrega_hoje", 0))
    c5.metric("🔴 Atrasados", dados.get("atrasados", 0), help="Não inclui pedidos já marcados como Pronto.")

    f1, f2, f3, f4 = st.columns(4)
    f1.metric("💵 Recebido hoje", _money(dados.get("recebido_hoje", 0)))
    f2.metric("💰 Previsto hoje", _money(dados.get("valor_previsto_hoje", 0)))
    f3.metric("📊 Carteira aberta", _money(dados.get("carteira_aberta", 0)))
    f4.metric("💬 Atendimentos", dados.get("atendimentos_abertos", 0))

    with st.expander("🎯 Alertas e diagnóstico do Alpha Core", expanded=False):
        for alerta in dados.get("alertas", []):
            st.write(f"• {alerta}")
        if indicadores_legados:
            comparacoes = {
                "Pedidos ativos": (dados.get("pedidos_ativos", 0), indicadores_legados.get("pedidos_ativos", 0)),
                "Aguardando aprovação": (dados.get("aguardando_aprovacao", 0), indicadores_legados.get("aguardando_aprovacao", 0)),
                "Prontos": (dados.get("prontos_aguardando_entrega", 0), indicadores_legados.get("prontos_operacionais", 0)),
                "Entregues hoje": (dados.get("entregues_hoje", 0), indicadores_legados.get("entregues_hoje", 0)),
                "Atrasados": (dados.get("atrasados", 0), indicadores_legados.get("atrasados_operacionais", 0)),
            }
            divergencias = [(nome, core, legado) for nome, (core, legado) in comparacoes.items() if int(core or 0) != int(legado or 0)]
            if divergencias:
                st.warning("Diagnóstico: ainda existem cálculos legados divergentes. O Centro Executivo já usa o Alpha Core.")
                for nome, core, legado in divergencias:
                    st.caption(f"{nome}: Alpha Core = {core} | cálculo legado = {legado}")
            else:
                st.success("Os principais indicadores estão sincronizados com o cálculo legado atual.")
        st.caption("Fonte única operacional compartilhada entre Jorge e Anna.")
