"""HF65.24.53: probe HTTP seguro para banco EXCLUSIVO de homologação.

Execução manual de backend:
 HF53_STAGING_SERVICE_KEY=... python scripts/hf65_24_53_staging_http_probe.py
Não usar credenciais de produção. Nenhum segredo é impresso.
Modo padrão só lê chave fictícia inexistente e verifica o 200 [].
A escrita opt-in (HF53_STAGING_ALLOW_PROBE_WRITE=YES) cria uma chave
aleatória identificada e a remove no finally, com conferência.
"""
from __future__ import annotations

import os
import secrets
import sys
from urllib.parse import urlsplit
from typing import Any
import requests

HOST = "hvaptsdhaxrdxgqqpicu.supabase.co"
BASE = f"https://{HOST}"
TABLE = BASE + "/rest/v1/app_data"
PREFIX = "hf53_http_probe_"


class ProbeError(RuntimeError):
    pass


def _check_target(base_url: str) -> None:
    parsed = urlsplit(base_url)
    if (parsed.scheme != "https" or parsed.hostname != HOST
            or parsed.port not in (None, 443)
            or parsed.username is not None or parsed.password is not None
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
        raise ProbeError("Banco diferente do projeto de homologação; operação cancelada.")


def _headers(key: str) -> dict[str, str]:
    if not isinstance(key, str) or not key.strip():
        raise ProbeError("Chave privada de homologação ausente.")
    h = {"apikey": key, "Content-Type": "application/json"}
    if not key.startswith("sb_secret_"):
        h["Authorization"] = "Bearer " + key
    return h


def _call(session: Any, method: str, *, key: str,
          headers: dict[str, str], body: dict | None = None,
          prefer: str | None = None):
    h = dict(headers)
    if prefer:
        h["Prefer"] = prefer
    kwargs: dict[str, Any] = {
        "headers": h,
        "params": {"key": "eq." + key, "select": "key,value"},
        "timeout": 10, "allow_redirects": False,
    }
    if body is not None:
        kwargs["json"] = body
    if method == "GET":
        response = session.get(TABLE, **kwargs)
    elif method == "POST":
        kwargs["params"] = {"on_conflict": "key", "select": "key,value"}
        response = session.post(TABLE, **kwargs)
    elif method == "DELETE":
        # A remoção é aceita somente para uma chave aleatória deste teste.
        if not key.startswith(PREFIX) or len(key) != len(PREFIX) + 32:
            raise ProbeError("Exclusão fora do prefixo de teste bloqueada.")
        response = session.delete(TABLE, **kwargs)
    else:
        raise ProbeError("Método não permitido.")
    if not isinstance(response.status_code, int) or not 200 <= response.status_code < 300:
        raise ProbeError(f"HTTP inesperado na homologação: {response.status_code}")
    return response.json()


def run_probe(*, base_url: str, service_key: str, write_enabled: bool = False,
              session: Any = None) -> str:
    _check_target(base_url)
    headers = _headers(service_key)
    if session is None:
        session = requests.Session()
    probe_key = PREFIX + secrets.token_hex(16)
    created = False
    try:
        before = _call(session, "GET", key=probe_key, headers=headers)
        if before != []:
            raise ProbeError("A chave aleatória de teste já existe ou leitura inesperada.")
        if not write_enabled:
            return "Leitura HTTP privada de homologação confirmada; nenhuma escrita."
        try:
            inserted = _call(session, "POST", key=probe_key, headers=headers,
                             body={"key": probe_key, "value": {"events": []}},
                             prefer="resolution=ignore-duplicates,return=representation")
            # Pode ter sido criada mesmo se o parse/retorno falhou.
            created = True
            if not (isinstance(inserted, list) and len(inserted) == 1
                    and inserted[0].get("key") == probe_key
                    and inserted[0].get("value") == {"events": []}):
                raise ProbeError("Inserção não retornou a linha esperada.")
            conflict = _call(session, "POST", key=probe_key, headers=headers,
                             body={"key": probe_key, "value": {"events": [{"bad": True}]}},
                             prefer="resolution=ignore-duplicates,return=representation")
            if conflict != []:
                raise ProbeError("Segundo INSERT não confirmou conflito preservado.")
            after = _call(session, "GET", key=probe_key, headers=headers)
            if after != inserted:
                raise ProbeError("Histórico foi alterado no conflito.")
            return "HTTP GET/POST e proteção contra sobrescrita confirmados em homologação."
        finally:
            # Limpeza também no caso em que o POST gravou, mas o retorno falhou.
            cleanup = _call(session, "DELETE", key=probe_key, headers=headers,
                            prefer="return=representation")
            if cleanup and (not isinstance(cleanup, list) or
                            any(row.get("key") != probe_key for row in cleanup)):
                raise ProbeError("Limpeza retornou documento diferente do teste.")
            remaining = _call(session, "GET", key=probe_key, headers=headers)
            if remaining != []:
                raise ProbeError("Não foi possível confirmar limpeza da chave de teste.")
    finally:
        # Não imprimir chaves, URLs com segredos ou respostas com conteúdo privado.
        pass


if __name__ == "__main__":
    try:
        print(run_probe(
            base_url=os.environ.get("HF53_STAGING_SUPABASE_URL", ""),
            service_key=os.environ.get("HF53_STAGING_SERVICE_KEY", ""),
            write_enabled=os.environ.get("HF53_STAGING_ALLOW_PROBE_WRITE") == "YES",
        ))
    except (ProbeError, requests.RequestException, ValueError) as exc:
        print("Falha segura na verificação HTTP de homologação: " + (
            str(exc) if isinstance(exc, ProbeError) else "comunicação indisponível"
        ), file=sys.stderr)
        sys.exit(1)
