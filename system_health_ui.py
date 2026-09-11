"""UI isolada de diagnóstico/boot do AlphaFest Manager.

HF26 — segunda etapa da organização interna gradual do app.py. Este módulo
apenas renderiza as abas de Saúde do sistema e Boot Manager já existentes.
Não altera persistência, regras operacionais nem feature flags.
"""
from __future__ import annotations

from typing import Callable, Any

import pandas as pd
import streamlit as st


def render_system_health_tab(*, diagnostico_sistema: Callable[[], dict[str, Any]]) -> None:
    """Renderiza Configurações → Núcleo Profissional → Saúde do sistema."""
    diag = diagnostico_sistema()
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Supabase", "🟢 Online" if diag["supabase_ok"] else "🟡 Contingência")
    d2.metric("Integridade", "🟢 OK" if diag["integridade_ok"] else "🔴 Atenção")
    d3.metric("Backup", "🟢 Atual" if diag["backup_ok"] else "🟡 Verificar")
    d4.metric("Estrutura de dados", f"v{diag['schema_version']}")
    st.caption(diag["supabase_mensagem"])
    if diag["backup_idade_horas"] is not None:
        st.caption(f"Último backup há aproximadamente {diag['backup_idade_horas']:.1f} hora(s).")
    if diag["problemas"]:
        for problema in diag["problemas"]:
            st.error(problema)
    else:
        st.success("Estruturas principais válidas.")
    st.write(
        f"Registros de auditoria: **{diag['auditorias']}** • "
        f"Itens recuperáveis na lixeira: **{diag['lixeira']}**"
    )
    if st.button("🔄 Executar diagnóstico novamente", key="health_refresh", use_container_width=True):
        st.rerun()


def render_boot_manager_tab(
    *,
    diagnostico_boot: Callable[[], dict[str, Any]],
    feature_flags: Callable[[], dict[str, Any]],
) -> None:
    """Renderiza Configurações → Núcleo Profissional → Boot Manager."""
    st.subheader("🚦 Boot Manager 14.2.5")
    st.caption("Diagnóstico exclusivo da Central do Jorge. Nenhuma configuração da Central da Anna é alterada.")
    registros_boot = diagnostico_boot()
    linhas_boot = []
    for nome_etapa, info_etapa in registros_boot.items():
        status_etapa = str(info_etapa.get("status", "ok"))
        icone = "🟢" if status_etapa == "ok" else ("🟡" if status_etapa in {"contingencia", "isolado"} else "🔴")
        linhas_boot.append({
            "Etapa": nome_etapa,
            "Estado": f"{icone} {status_etapa}",
            "Tempo (s)": round(float(info_etapa.get("duracao", 0.0) or 0.0), 3),
            "Detalhe": str(info_etapa.get("detalhe", "")),
        })
    st.dataframe(pd.DataFrame(linhas_boot), use_container_width=True, hide_index=True)
    flags_boot = feature_flags()
    st.markdown("#### Chaves de segurança")
    st.json(flags_boot, expanded=False)
    st.info("Preview, IA e Campanha Mestre permanecem desligados até homologação na Central do Jorge.")
    if st.button("🔄 Atualizar diagnóstico do boot", key="boot1424_refresh", use_container_width=True):
        st.rerun()
