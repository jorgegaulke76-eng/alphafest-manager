"""HF65.24.53 — conferência da publicação e rascunhos editoriais por sessão.

Regras sem Streamlit, rede ou gravação automática. A assinatura usa exatamente
o mesmo payload que alimenta o cache do pacote público.
"""
from __future__ import annotations

import copy
from collections.abc import MutableMapping
from typing import Any

from document_runtime_service import stable_signature


EDITORIAL_DOCUMENT_KEYS = frozenset({
    "site_campaign_db", "site_home_content_db",
    "site_dicas_multicanal_db", "site_posts_comerciais_db",
})
PREVIEW_HTML = "site_hf59_html_preview"
PREVIEW_VERSION = "site_hf59_preview_app_version"
PREVIEW_SIGNATURE = "site_hf53_preview_signature"
CONFIRMATION = "site_hf59_confirmar_publicacao"


def preview_matches(state: MutableMapping[str, Any], version: str, payload: Any) -> bool:
    return bool(
        state.get(PREVIEW_HTML)
        and state.get(PREVIEW_VERSION) == version
        and state.get(PREVIEW_SIGNATURE) == stable_signature(payload)
    )


def invalidate_changed_preview(state: MutableMapping[str, Any], version: str, payload: Any) -> bool:
    """Limpa só a prévia/confirmação obsoleta; retorna se havia prévia visível."""
    if preview_matches(state, version, payload):
        return False
    had_preview = bool(state.get(PREVIEW_HTML))
    for key in (PREVIEW_HTML, PREVIEW_SIGNATURE, CONFIRMATION):
        state.pop(key, None)
    return had_preview


def remember_preview(state: MutableMapping[str, Any], html: str, version: str, payload: Any) -> None:
    if not str(html or "").strip():
        raise ValueError("A prévia gerada está vazia.")
    state[PREVIEW_HTML] = html
    state[PREVIEW_VERSION] = version
    state[PREVIEW_SIGNATURE] = stable_signature(payload)
    # Uma nova conferência é necessária mesmo quando a pessoa pede reconstrução.
    state.pop(CONFIRMATION, None)


def editorial_snapshot(state: MutableMapping[str, Any], key: str, current: Any) -> Any:
    """Mantém a base que originou os campos, inclusive após expirar o cache."""
    if key not in EDITORIAL_DOCUMENT_KEYS:
        raise ValueError("Documento não editorial.")
    bases = state.setdefault("_site_editorial_bases_hf53", {})
    if key not in bases:
        bases[key] = copy.deepcopy(current)
    return copy.deepcopy(bases[key])


def editorial_expected(state: MutableMapping[str, Any], key: str, fallback: Any) -> Any:
    bases = state.get("_site_editorial_bases_hf53", {})
    return copy.deepcopy(bases[key] if key in bases else fallback)


def remember_editorial_draft(state: MutableMapping[str, Any], key: str, value: Any) -> None:
    if key in EDITORIAL_DOCUMENT_KEYS:
        state.setdefault("_site_editorial_drafts_hf53", {})[key] = copy.deepcopy(value)


def editorial_saved(state: MutableMapping[str, Any], key: str, value: Any) -> None:
    if key not in EDITORIAL_DOCUMENT_KEYS:
        return
    state.setdefault("_site_editorial_bases_hf53", {})[key] = copy.deepcopy(value)
    state.setdefault("_site_editorial_drafts_hf53", {}).pop(key, None)
    revisions = state.setdefault("_site_editorial_revisions_hf53", {})
    revisions[key] = int(revisions.get(key, 0)) + 1


def refresh_editorial_bases(state: MutableMapping[str, Any]) -> None:
    """Recarga explícita troca as bases; rascunhos recusados ficam recuperáveis."""
    state.pop("_site_editorial_bases_hf53", None)
    revisions = state.setdefault("_site_editorial_revisions_hf53", {})
    for key in EDITORIAL_DOCUMENT_KEYS:
        revisions[key] = int(revisions.get(key, 0)) + 1
    for key in (PREVIEW_HTML, PREVIEW_SIGNATURE, CONFIRMATION):
        state.pop(key, None)
