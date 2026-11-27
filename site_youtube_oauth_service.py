"""HF65.23 — conexão OAuth 2.0 do canal YouTube oficial, com persistência cifrada.

Os segredos são configurados *somente* no painel Secrets do Streamlit. Tokens de
atualização nunca aparecem no HTML, GitHub ou documentos do Manager em texto claro.
O callback usa state HMAC curto, verifica e-mail Google e canal antes de persistir.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Dict
from urllib.parse import urlencode

import requests
from cryptography.fernet import Fernet, InvalidToken

REDIRECT_URI_OFICIAL = "https://alphafest-manager-msbdyvs7cg2zxzqmxzbqu5.streamlit.app/"
CANAL_HANDLE = "@AlphafestItatiba2026"
CANAL_URL = "https://www.youtube.com/@AlphafestItatiba2026"
ESCOPOS = (
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
)
EMAILS_PERMITIDOS = frozenset({"alphafesti@gmail.com", "jorgegaulke76@gmail.com"})


class ErroYoutubeOAuth(RuntimeError):
    pass


def config_oauth(entrada: Any) -> Dict[str, str]:
    if not isinstance(entrada, dict):
        try:
            entrada = dict(entrada)
        except Exception:
            entrada = {}
    campos = ("client_id", "client_secret", "redirect_uri", "fernet_key")
    conf = {c: str(entrada.get(c, "") or "").strip() for c in campos}
    if not conf["redirect_uri"]:
        conf["redirect_uri"] = REDIRECT_URI_OFICIAL
    return conf


def configurado(conf: Dict[str, str]) -> bool:
    if not all(conf.get(x) for x in ("client_id", "client_secret", "fernet_key")):
        return False
    if conf.get("redirect_uri") != REDIRECT_URI_OFICIAL:
        return False
    try:
        Fernet(conf["fernet_key"].encode("ascii"))
    except Exception:
        return False
    return True


def _chave_hmac(conf: Dict[str, str]) -> bytes:
    # A chave do state é derivada de uma chave estável fornecida em Secrets.
    if not configurado(conf):
        raise ErroYoutubeOAuth("Configure as credenciais OAuth e a chave cifrada em Streamlit Secrets.")
    return hashlib.sha256((conf["fernet_key"] + ":oauth-state").encode()).digest()


def gerar_estado(conf: Dict[str, str]) -> str:
    payload = json.dumps({"iat": int(time.time()), "nonce": secrets.token_urlsafe(20),
                          "type": "alphafest-youtube"}, separators=(",", ":")).encode()
    encoded = base64.urlsafe_b64encode(payload).rstrip(b"=").decode()
    assinatura = hmac.new(_chave_hmac(conf), encoded.encode(), hashlib.sha256).hexdigest()
    return "afyt1." + encoded + "." + assinatura


def verificar_estado(state: str, conf: Dict[str, str], *, now: int | None = None) -> bool:
    try:
        prefixo, encoded, assinatura = str(state or "").split(".")
        if prefixo != "afyt1" or len(encoded) > 512 or len(assinatura) != 64:
            return False
        esperado = hmac.new(_chave_hmac(conf), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(assinatura, esperado):
            return False
        corpo = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        agora = int(time.time() if now is None else now)
        return (corpo.get("type") == "alphafest-youtube" and
                isinstance(corpo.get("nonce"), str) and len(corpo["nonce"]) >= 16 and
                isinstance(corpo.get("iat"), int) and 0 <= agora - corpo["iat"] <= 600)
    except Exception:
        return False


def url_autorizacao(conf: Dict[str, str]) -> str:
    if not configurado(conf):
        raise ErroYoutubeOAuth("Configure client_id, client_secret e fernet_key no Streamlit.")
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
        "response_type": "code", "client_id": conf["client_id"],
        "redirect_uri": REDIRECT_URI_OFICIAL,
        "scope": " ".join(ESCOPOS), "access_type": "offline", "prompt": "consent select_account",
        "include_granted_scopes": "false", "state": gerar_estado(conf),
    })


def _get_json(url: str, access_token: str, *, params: dict | None = None) -> dict:
    response = requests.get(url, headers={"Authorization": f"Bearer {access_token}"},
                            params=params, timeout=18)
    response.raise_for_status()
    obj = response.json()
    if not isinstance(obj, dict):
        raise ErroYoutubeOAuth("Resposta inesperada do Google.")
    return obj


def _normalizar_handle(s: str) -> str:
    return str(s or "").strip().lstrip("@").casefold()


def trocar_codigo_e_validar(code: str, state: str, conf: Dict[str, str]) -> Dict[str, str]:
    if not verificar_estado(state, conf):
        raise ErroYoutubeOAuth("Autorização expirada ou inválida. Inicie a conexão novamente.")
    if not code or len(code) > 4096:
        raise ErroYoutubeOAuth("O Google não retornou um código de autorização válido.")
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "code": code, "client_id": conf["client_id"], "client_secret": conf["client_secret"],
        "redirect_uri": REDIRECT_URI_OFICIAL, "grant_type": "authorization_code",
    }, timeout=22)
    resp.raise_for_status()
    tokens = resp.json()
    access = str(tokens.get("access_token", ""))
    refresh = str(tokens.get("refresh_token", ""))
    if not access or not refresh:
        raise ErroYoutubeOAuth("O Google não retornou autorização duradoura. Reconecte com consentimento.")
    usuario = _get_json("https://openidconnect.googleapis.com/v1/userinfo", access)
    email = str(usuario.get("email", "")).strip().casefold()
    if email not in EMAILS_PERMITIDOS or usuario.get("email_verified") is not True:
        raise ErroYoutubeOAuth("Conta Google não autorizada para administrar o canal da AlphaFest.")
    canais = _get_json("https://www.googleapis.com/youtube/v3/channels", access,
                       params={"part": "snippet", "mine": "true", "maxResults": 50}).get("items", [])
    if not isinstance(canais, list):
        raise ErroYoutubeOAuth("Não foi possível identificar o canal vinculado.")
    correspondentes = [c for c in canais if _normalizar_handle(c.get("snippet", {}).get("customUrl", "")) == _normalizar_handle(CANAL_HANDLE)]
    if len(correspondentes) != 1:
        raise ErroYoutubeOAuth("O canal autenticado não corresponde a @AlphafestItatiba2026. Selecione o canal correto no Google.")
    canal = correspondentes[0]
    canal_id = str(canal.get("id", ""))
    if not re.fullmatch(r"UC[A-Za-z0-9_-]{22}", canal_id):
        raise ErroYoutubeOAuth("Identificador do canal não confirmado pelo YouTube.")
    cifra = Fernet(conf["fernet_key"].encode("ascii")).encrypt(refresh.encode("utf-8")).decode("ascii")
    return {"refresh_token_cifrado": cifra, "channel_id": canal_id,
            "channel_title": str(canal.get("snippet", {}).get("title", "AlphaFest"))[:120],
            "email": email, "connected_at": datetime.now(timezone.utc).isoformat()}


def credenciais_upload(registro: Dict[str, str], conf: Dict[str, str]) -> Dict[str, str]:
    if not configurado(conf):
        raise ErroYoutubeOAuth("Segredos OAuth ausentes ou incorretos.")
    if not re.fullmatch(r"UC[A-Za-z0-9_-]{22}", str(registro.get("channel_id", ""))):
        raise ErroYoutubeOAuth("Ainda não existe um canal verificado.")
    try:
        refresh = Fernet(conf["fernet_key"].encode("ascii")).decrypt(
            str(registro.get("refresh_token_cifrado", "")).encode("ascii")
        ).decode("utf-8")
    except (InvalidToken, ValueError, TypeError) as exc:
        raise ErroYoutubeOAuth("Não foi possível validar a autorização salva.") from exc
    return {"client_id": conf["client_id"], "client_secret": conf["client_secret"],
            "refresh_token": refresh}


def conferir_canal_no_token(access_token: str, esperado: str) -> bool:
    canais = _get_json("https://www.googleapis.com/youtube/v3/channels", access_token,
                       params={"part": "id", "mine": "true"}).get("items", [])
    return any(str(c.get("id", "")) == esperado for c in canais if isinstance(c, dict))
