"""HF53: leitura E2E SOMENTE das tres fixtures sinteticas da homologacao.

Não aceita chaves oficiais nem fornece relatório privado. Fluxo HTTP
GET exclusivamente de fixture, com login Google de diagnóstico e segredo
de servidor. Apenas agregados são mostrados; nenhum documento bruto.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from commercial_server_session_postgrest import _endpoint
from commercial_official_snapshot_adapter import sanitize_official_manager_snapshots
from commercial_verified_report import build_verified_commercial_report
from hf65_24_53_http_diagnostic import _eligible

PREFIX = "hf53_fixture_20261124_"
KEYS = (PREFIX + "propostas", PREFIX + "atendimentos", PREFIX + "atribuicoes")


def _read_fixture(
    *, get: Callable[..., Any], endpoint: str,
    headers: Mapping[str, str], key: str,
) -> dict[str, Any]:
    if key not in KEYS:
        raise ValueError()
    response = get(
        endpoint, headers=dict(headers),
        params={"select": "value", "key": "eq." + key, "limit": "2"},
        timeout=10, allow_redirects=False,
    )
    response.raise_for_status()
    if (type(response.status_code) is not int or not 200 <= response.status_code < 300):
        raise ValueError()
    rows = response.json()
    if (not isinstance(rows, list) or len(rows) != 1
        or not isinstance(rows[0], dict) or set(rows[0]) != {"value"}
        or not isinstance(rows[0]["value"], dict)):
        raise ValueError()
    return rows[0]["value"]


def read_staging_synthetic_commercial_report(
    *, get: Callable[..., Any], base_url: str, headers: Mapping[str, str],
) -> dict[str, Any]:
    """Sempre falha fechado, sem fallback e sem acessar chaves oficiais."""
    try:
        endpoint = _endpoint(base_url, headers).rsplit("/", 1)[0] + "/app_data"
        docs = [_read_fixture(get=get, endpoint=endpoint, headers=headers, key=key) for key in KEYS]
        if (set(docs[0]) != {"itens"} or set(docs[1]) != {"config", "itens"}
            or set(docs[2]) != {"events"} or not isinstance(docs[2]["events"], list)):
            raise ValueError()
        proposals, contacts = sanitize_official_manager_snapshots(
            historico_orcamentos=docs[0]["itens"],
            atendimentos_db=docs[1],
        )
        events = docs[2]["events"]
        if (len(proposals) != 3 or len(contacts) != 3 or len(events) != 3
            or any(not p["numero_proposta"].startswith("HF53-DEMO-") for p in proposals)
            or any(not c["id"].startswith("HF53-DEMO-") for c in contacts)
            or any(not isinstance(e, dict) or
                   not str(e.get("numero_proposta","")).startswith("HF53-DEMO-")
                   for e in events)):
            raise ValueError()
        return build_verified_commercial_report(contacts, proposals, events)
    except Exception:
        raise PermissionError("Demonstração sintética indisponível ou inconsistente.") from None


def render_staging_synthetic_report(st: Any, *, get: Callable[..., Any] | None = None) -> None:
    st.subheader("Teste integrado no banco — dados 100% fictícios")
    allowed, _reason = _eligible(st)
    if not allowed:
        st.caption("Diagnóstico privado indisponível.")
        return
    st.caption("Lê apenas 3 documentos de demonstração; não acessa cadastros reais.")
    if not st.button("Conferir cálculo integrado no Supabase de testes"):
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
        report = read_staging_synthetic_commercial_report(
            get=get, base_url=url, headers=headers,
        )
        if (report["pedidos_pagos_atribuidos"] != 2
            or report["receita_atribuida"] != 200):
            raise ValueError()
    except Exception:
        st.error("Cálculo integrado não confirmado; relatório real permanece fechado.")
        return
    st.success("Homologação HTTP sintética: 2 pedidos atribuídos, R$ 200,00 comerciais.")
    st.caption("Esse valor NÃO comprova recebimento bancário. Nenhum cliente real foi consultado.")
