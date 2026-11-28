"""HF65.24.53 — prontidão dos documentos em HOMOLOGAÇÃO, só metadados.

Não consulta value (dados dos clientes), não grava documentos, não habilita
relatório privado. Reaproveita as credenciais do backend somente após OIDC
Google e allowlist do diagnóstico. Falha fechado se HTTP não confirmar.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from commercial_server_session_postgrest import _endpoint
from hf65_24_53_http_diagnostic import _eligible, STAGING_URL

EXPECTED = (
    ("historico_orcamentos", "Propostas"),
    ("atendimentos_db", "Atendimentos"),
    ("hf65_24_53_attribution_events_private_db", "Atribuições auditadas"),
)


def check_staging_document_presence(
    *, get: Callable[..., Any], base_url: str, headers: Mapping[str, str],
) -> dict[str, bool]:
    """Retorna somente existência 0/1. Não lê value nem IDs de clientes."""
    try:
        endpoint = _endpoint(base_url, headers).rsplit("/", 1)[0] + "/app_data"
        if not callable(get):
            raise ValueError()
        result = {}
        for key, _label in EXPECTED:
            response = get(
                endpoint, headers=dict(headers),
                params={"select": "key", "key": "eq." + key, "limit": "2"},
                timeout=10, allow_redirects=False,
            )
            response.raise_for_status()
            if type(response.status_code) is not int or not 200 <= response.status_code < 300:
                raise ValueError()
            rows = response.json()
            if (not isinstance(rows, list) or len(rows) > 1
                or any(not isinstance(row, dict) or set(row) != {"key"}
                       or row["key"] != key for row in rows)):
                raise ValueError()
            result[key] = len(rows) == 1
        return result
    except Exception:
        raise PermissionError("Não foi possível confirmar a prontidão do staging.") from None


def render_staging_readiness(st: Any, *, get: Callable[..., Any] | None = None) -> None:
    """Diagnóstico acessível apenas ao operador de testes; sem acessar valores."""
    st.subheader("Prontidão dos documentos — homologação")
    allowed, reason = _eligible(st)
    if not allowed:
        st.caption(reason or "Diagnóstico indisponível.")
        return
    st.caption("Consulta somente a existência dos três documentos; nenhum conteúdo é lido.")
    if not st.button("Verificar documentos da homologação"):
        return
    try:
        if get is None:
            import requests
            get = requests.get
        url = st.secrets["HF53_STAGING_SUPABASE_URL"]
        key = st.secrets["HF53_STAGING_SERVICE_KEY"]
        headers = {"apikey": key}
        if not key.startswith("sb_secret_"):
            headers["Authorization"] = "Bearer " + key
        status = check_staging_document_presence(get=get, base_url=url, headers=headers)
    except Exception:
        st.error("Verificação indisponível. Nenhum documento comercial foi aberto.")
        return
    for key, label in EXPECTED:
        st.caption(f"{label}: {'presente' if status[key] else 'ausente'}")
    if all(status.values()):
        st.info("Três documentos presentes. Presença não comprova integridade ou autorização de acesso.")
    else:
        st.warning("Homologação comercial ainda bloqueada: faltam documentos autorizados e saneados.")
