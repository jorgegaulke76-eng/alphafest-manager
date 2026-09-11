"""UI isolada da Auditoria/Saneamento do AlphaFest Manager.

HF29 — quinta etapa da organização interna gradual do app.py. Este módulo apenas
renderiza Configurações → Núcleo Profissional → Auditoria e recebe por injeção
as funções de leitura, auditoria e saneamento já homologadas. Nenhuma regra de
status, persistência ou reconciliação operacional é alterada.
"""
from __future__ import annotations

import copy
import json
from datetime import datetime
from typing import Any, Callable

import pandas as pd
import streamlit as st


def render_audit_tab(
    *,
    executar_auditoria_sincronizacao_operacional: Callable[..., dict[str, Any]],
    renderizar_auditoria_sincronizacao_operacional: Callable[..., Any],
    planejar_saneamento_status: Callable[[Any], dict[str, Any]],
    carregar_historico: Callable[..., Any],
    renderizar_previa_saneamento_status: Callable[[dict[str, Any]], Any],
    executar_saneamento_status_historicos_seguro: Callable[[], dict[str, Any]],
    carregar_auditoria: Callable[[], list[dict[str, Any]]],
    fmt_valor_auditoria: Callable[[Any], str],
    agora_local: Callable[[], Any],
    hoje_local: Callable[[], Any],
) -> None:
    """Renderiza a aba Auditoria mantendo o comportamento homologado no app.py."""
    st.subheader("🔗 Auditoria de Sincronização Operacional · HF7")
    st.caption(
        "Compara Histórico, Fluxo/Produção, Risco e Entregas usando leitura fresca. "
        "O reparo automático normal continua restrito ao espelho do Fluxo; status oficiais só podem ser completados "
        "pelo saneamento histórico seguro abaixo, com prévia e confirmação explícita."
    )
    if st.button("🔄 Auditar e sincronizar telas agora", key="hf7_auditar_sincronizar", use_container_width=True, type="primary"):
        with st.spinner("Conferindo a Fonte Única e reconciliando projeções seguras..."):
            rel_manual_hf7 = executar_auditoria_sincronizacao_operacional(force_refresh=True, registrar=True)
        renderizar_auditoria_sincronizacao_operacional(rel_manual_hf7, expandido=True)
    elif st.session_state.get("_i8134_relatorio_sincronizacao"):
        renderizar_auditoria_sincronizacao_operacional(
            st.session_state.get("_i8134_relatorio_sincronizacao"), expandido=False
        )

    st.divider()
    st.markdown("### 🧹 Saneamento seguro de status históricos · HF7")
    st.caption(
        "Completa somente pré-requisitos obrigatórios: Entregue → Pronto; Pronto → Aprovado; Pago → Aprovado. "
        "Nunca infere Pago, nunca desfaz status, não altera estoque e não cria datas retroativas."
    )
    if st.button("🔍 Preparar prévia do saneamento", key="hf7_preparar_saneamento", use_container_width=True):
        plano_hf7 = planejar_saneamento_status(carregar_historico(force_refresh=True))
        st.session_state["_i8134_hf7_previa_saneamento"] = copy.deepcopy(plano_hf7)
    plano_hf7 = st.session_state.get("_i8134_hf7_previa_saneamento")
    if isinstance(plano_hf7, dict):
        renderizar_previa_saneamento_status(plano_hf7)
        if int(plano_hf7.get("alteracoes", 0) or 0) > 0:
            confirmar_hf7 = st.checkbox(
                "Confirmo aplicar somente as correções seguras mostradas acima.",
                key="hf7_confirmar_saneamento",
            )
            if st.button(
                "🧹 Corrigir inconsistências históricas seguras",
                key="hf7_aplicar_saneamento",
                use_container_width=True,
                type="primary",
                disabled=not confirmar_hf7,
            ):
                with st.spinner("Aplicando correções uma proposta por vez e confirmando no banco..."):
                    resultado_hf7 = executar_saneamento_status_historicos_seguro()
                st.session_state["_i8134_hf7_previa_saneamento"] = copy.deepcopy(resultado_hf7.get("plano_restante") or {})
                if resultado_hf7.get("falhas"):
                    st.warning(
                        f"{resultado_hf7.get('alteracoes_confirmadas', 0)} correção(ões) confirmada(s); "
                        f"{len(resultado_hf7.get('falhas') or [])} proposta(s) exigem nova tentativa/revisão."
                    )
                    st.dataframe(pd.DataFrame(resultado_hf7.get("falhas") or []), use_container_width=True, hide_index=True)
                else:
                    st.success(
                        f"✅ {resultado_hf7.get('alteracoes_confirmadas', 0)} correção(ões) histórica(s) confirmada(s) no banco. "
                        "Projeções operacionais reconciliadas em seguida."
                    )
                renderizar_auditoria_sincronizacao_operacional(
                    resultado_hf7.get("sincronizacao") or {}, expandido=True
                )

    st.divider()
    auditoria = carregar_auditoria()
    if not auditoria:
        st.info("A auditoria começará a registrar backups, migrações, exclusões e restaurações.")
        return

    filtro_acao = st.text_input(
        "Filtrar auditoria",
        placeholder="Usuário, ação, entidade ou identificador",
        key="audit_filter",
    ).strip().casefold()
    exibidos = []
    for reg in auditoria:
        detalhes_busca = reg.get("detalhes") if isinstance(reg.get("detalhes"), dict) else {}
        texto = " ".join(str(reg.get(k, "")) for k in ["usuario", "acao", "entidade", "identificador", "resultado"])
        texto += " " + json.dumps(detalhes_busca, ensure_ascii=False, default=str)
        texto = texto.casefold()
        if not filtro_acao or filtro_acao in texto:
            exibidos.append(reg)

    linhas = []
    for reg in exibidos[:500]:
        try:
            data_fmt = datetime.fromisoformat(reg.get("data_hora", "")).astimezone(agora_local().tzinfo).strftime("%d/%m/%Y %H:%M:%S")
        except Exception:
            data_fmt = reg.get("data_hora", "")
        detalhes_reg = reg.get("detalhes") if isinstance(reg.get("detalhes"), dict) else {}
        mudanca_reg = ""
        if detalhes_reg.get("campo"):
            mudanca_reg = (
                f"{detalhes_reg.get('campo')}: "
                f"{fmt_valor_auditoria(detalhes_reg.get('valor_anterior'))} → "
                f"{fmt_valor_auditoria(detalhes_reg.get('valor_novo'))}"
            )
        linhas.append({
            "Data": data_fmt,
            "Usuário": reg.get("usuario"),
            "Ação": reg.get("acao"),
            "Mudança": mudanca_reg,
            "Origem": detalhes_reg.get("origem") or reg.get("entidade"),
            "Entidade": reg.get("entidade"),
            "Identificador": reg.get("identificador"),
            "Resultado": reg.get("resultado"),
        })
    st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Exportar auditoria JSON",
        json.dumps(auditoria, ensure_ascii=False, indent=2),
        file_name=f"auditoria_festmanager_{hoje_local().isoformat()}.json",
        mime="application/json",
        use_container_width=True,
    )
