"""Testa API PostgREST REAL conectada a Postgres DESCARTÁVEL no CI.

Não usa credenciais Supabase, Cloudflare ou dados de clientes.
O endpoint é o PostgREST direto, sem o gateway `/rest/v1` do Supabase.
"""
from __future__ import annotations

import os
import requests

BASE = os.environ.get("HF52_LOCAL_POSTGREST", "http://127.0.0.1:3000").rstrip("/")
TABLE = BASE + "/site_metrics_events"
HEADERS = {"Content-Type": "application/json", "Prefer": "return=minimal"}


def expect_status(result, status: int) -> None:
    assert result.status_code == status, (
        f"HTTP {result.status_code} (esperado {status}): {result.text[:300]}"
    )


def main() -> None:
    # As três categorias críticas podem ser gravadas com o papel público,
    # sem permissão de ler registros já persistidos.
    for event, context in [
        ("page_view", "page"),
        ("product_open", "campaign_product"),
        ("whatsapp_click", "site"),
    ]:
        payload = {
            "event_type": event,
            "product_name": "Bubble de teste",
            "page_path": "/",
            "entry_path": "/",
            "client_id": "hf52-client-local",
            "session_id": "hf52-session-local",
            "traffic_source": "instagram",
            "utm_source": "instagram",
            "utm_medium": "stories",
            "utm_campaign": "hf52-local-contrato",
            "event_context": context,
        }
        resp = requests.post(TABLE, headers=HEADERS, json=payload, timeout=15)
        expect_status(resp, 201)

    # O papel anon NÃO pode consultar, alterar ou apagar eventos.
    read = requests.get(TABLE, timeout=15)
    assert read.status_code in (401, 403), (
        f"GET público não deveria ser permitido: HTTP {read.status_code}"
    )
    update = requests.patch(
        TABLE + "?event_type=eq.page_view",
        headers=HEADERS,
        json={"utm_campaign": "manipulado"},
        timeout=15,
    )
    assert update.status_code in (401, 403), (
        f"UPDATE público não deveria ser permitido: HTTP {update.status_code}"
    )

    # A política RLS recusa eventos desconhecidos e valores excessivos.
    for invalid in [
        {"event_type": "compra_confirmada"},
        {"event_type": "whatsapp_click", "utm_campaign": "x" * 181},
    ]:
        resp = requests.post(TABLE, headers=HEADERS, json=invalid, timeout=15)
        assert 400 <= resp.status_code < 500, (
            f"Payload inválido aceito pelo banco: HTTP {resp.status_code}"
        )
    print(
        "PostgREST + PostgreSQL isolados: 3 eventos gravados, GET/PATCH públicos "
        "bloqueados e 2 payloads inválidos rejeitados. Sem Supabase de produção.",
        flush=True,
    )


if __name__ == "__main__":
    main()
