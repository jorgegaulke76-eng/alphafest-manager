"""UI isolada da Lixeira do AlphaFest Manager.

HF27 — terceira etapa da organização interna gradual do app.py. O módulo apenas
renderiza a aba Configurações → Núcleo Profissional → Lixeira e recebe por
injeção as funções de persistência já existentes. Nenhuma regra de exclusão ou
restauração foi alterada.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

import streamlit as st


def render_trash_tab(
    *,
    carregar_lixeira: Callable[[], list[dict[str, Any]]],
    restaurar_item_lixeira: Callable[[dict[str, Any]], Any],
    remover_da_lixeira: Callable[[Any], Any],
    registrar_auditoria: Callable[..., Any],
    agora_local: Callable[[], Any],
) -> None:
    """Renderiza a Lixeira mantendo o comportamento homologado no app.py."""
    lixeira = carregar_lixeira()
    if not lixeira:
        st.success("A lixeira está vazia.")
        return

    st.warning(f"{len(lixeira)} item(ns) podem ser restaurados. A remoção definitiva exige confirmação.")
    for reg in lixeira[:200]:
        try:
            dt_fmt = datetime.fromisoformat(reg.get("excluido_em", "")).astimezone(agora_local().tzinfo).strftime("%d/%m/%Y %H:%M")
        except Exception:
            dt_fmt = reg.get("excluido_em", "")

        with st.expander(f"{reg.get('tipo')} — {reg.get('identificador') or 'sem identificação'} — {dt_fmt}"):
            st.caption(f"Movido por: {reg.get('excluido_por', 'Não informado')}")
            st.json(reg.get("item", {}), expanded=False)
            r1, r2 = st.columns(2)
            if r1.button("♻️ Restaurar", key=f"lix_restore_{reg.get('id_lixeira')}", use_container_width=True):
                try:
                    restaurar_item_lixeira(reg)
                    st.success("Item restaurado.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Não foi possível restaurar: {exc}")

            confirm = r2.checkbox("Confirmar remoção definitiva", key=f"lix_confirm_{reg.get('id_lixeira')}")
            if st.button(
                "❌ Remover definitivamente",
                key=f"lix_purge_{reg.get('id_lixeira')}",
                disabled=not confirm,
                use_container_width=True,
            ):
                remover_da_lixeira(reg.get("id_lixeira"))
                registrar_auditoria(
                    "Remover definitivamente",
                    reg.get("tipo", "Item"),
                    reg.get("identificador", ""),
                )
                st.rerun()
