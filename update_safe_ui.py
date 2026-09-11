"""Tela isolada de Atualização Segura do AlphaFest Manager.

HF25 — primeiro passo da organização interna gradual do app.py. O módulo apenas
renderiza a aba já existente e recebe por injeção as funções operacionais; não
altera persistência, regras de negócio ou a lógica dos diagnósticos.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Any

import streamlit as st


def render_update_safe_tab(
    *,
    root_dir: Path,
    version_app: str,
    version_data: str,
    diagnostico_sistema: Callable[[], dict[str, Any]],
    criar_backup_completo: Callable[..., dict[str, Any]],
    registrar_auditoria: Callable[..., Any],
    backup_para_zip_bytes: Callable[[dict[str, Any]], bytes],
) -> None:
    """Renderiza Configurações → Atualização segura sem depender de app.py."""
    st.info(
        "Antes de publicar uma nova versão, gere um ponto de restauração e anote as contagens. "
        "O pacote de atualização deve conter somente código e migrações, nunca os dados da empresa."
    )
    diag_pre = diagnostico_sistema()

    try:
        from update_hygiene import runtime_integrity_check
        preflight = runtime_integrity_check(Path(root_dir))
    except Exception as exc:
        preflight = None
        st.warning(f"Preflight técnico indisponível: {exc}")

    if preflight is not None:
        if preflight.ok:
            st.success("Preflight de atualização: runtime íntegro e Template Mestre HF7 protegido.")
        else:
            st.error("Preflight de atualização reprovado: " + " • ".join(preflight.problems))
        for warning in preflight.warnings:
            st.caption(f"ℹ️ {warning}")

    try:
        from release_diagnostics import run_release_diagnostics
        release_diag = run_release_diagnostics(Path(root_dir))
    except Exception as exc:
        release_diag = None
        st.warning(f"Diagnóstico da release indisponível: {exc}")

    if release_diag is not None:
        tests = release_diag.test_inventory
        if release_diag.ok:
            st.success(
                "Diagnóstico da release: OK • "
                f"{tests.portable_files + tests.current_release_files} teste(s) atual(is)/portável(is) • "
                f"{tests.historical_version_files} histórico(s) separado(s)."
            )
        else:
            st.error("Diagnóstico da release reprovado: " + " • ".join(release_diag.problems))
        for warning in release_diag.warnings:
            st.caption(f"🧪 {warning}")

    st.json({
        "versao_app": version_app,
        "versao_dados": version_data,
        "contagens_antes_atualizacao": diag_pre["contagens"],
        "supabase": diag_pre["supabase_mensagem"],
        "integridade": "OK" if diag_pre["integridade_ok"] else diag_pre["problemas"],
        "preflight_update": (
            {
                "status": "OK" if preflight.ok else "REPROVADO",
                "versao": preflight.version,
                "problemas": preflight.problems,
                "avisos": preflight.warnings,
            } if preflight is not None else {"status": "INDISPONÍVEL"}
        ),
        "diagnostico_release_hf23": (
            {
                "status": "OK" if release_diag.ok else "REPROVADO",
                "versao": release_diag.version,
                "problemas": release_diag.problems,
                "avisos": release_diag.warnings,
                "testes": release_diag.test_inventory.to_dict(),
                "checks": release_diag.checks,
            } if release_diag is not None else {"status": "INDISPONÍVEL"}
        ),
    }, expanded=False)

    update_blocked = bool(
        (preflight is not None and not preflight.ok)
        or (release_diag is not None and not release_diag.ok)
    )
    if st.button(
        "🛡️ Preparar atualização segura",
        type="primary",
        key="preparar_update_seguro",
        use_container_width=True,
        disabled=update_blocked,
    ):
        try:
            backup = criar_backup_completo(
                tipo="antes_atualizacao",
                protegido=True,
                motivo=f"Ponto de restauração antes de atualizar a partir da versão {version_app}",
            )
            registrar_auditoria(
                "Preparar atualização",
                "Sistema",
                version_app,
                {"backup_id": backup.get("backup_id"), "contagens": backup.get("contagens")},
            )
            st.success(f"Atualização preparada. Backup protegido: {backup.get('backup_id')}")
            st.download_button(
                "⬇️ Baixar ponto de restauração",
                data=backup_para_zip_bytes(backup),
                file_name=f"antes_atualizacao_{backup.get('backup_id')}.zip",
                mime="application/zip",
                use_container_width=True,
            )
        except Exception as exc:
            st.error(f"Falha ao preparar atualização: {exc}")
