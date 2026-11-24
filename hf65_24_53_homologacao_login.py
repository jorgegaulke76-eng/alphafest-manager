"""HF65.24.53 — diagnóstico OIDC independente, sem acesso a clientes.

Este arquivo pode ser iniciado isoladamente em um novo app Streamlit de
HOMOLOGAÇÃO. Não é importado no app.py de produção.
Não exibe e-mail, sujeito, token ou credencial, apenas flags booleanas.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


NEEDED = ("sub", "iss", "aud", "sid", "iat", "exp")


def oidc_readiness(st: Any) -> dict[str, Any]:
    """Diagnostica somente presença de claims e da configuração de login."""
    try:
        auth_config = st.secrets.get("auth")
        configured = isinstance(auth_config, Mapping) and all(
            bool(auth_config.get(name)) for name in
            ("redirect_uri", "cookie_secret", "client_id", "client_secret", "server_metadata_url")
        )
    except Exception:
        configured = False
    try:
        user = st.user
        logged_in = user.is_logged_in is True
        claims = user.to_dict() if logged_in else {}
        if not isinstance(claims, Mapping):
            claims = {}
    except Exception:
        logged_in = False
        claims = {}

    present = {name: claims.get(name) is not None for name in NEEDED}
    return {
        "oidc_configured": configured,
        "logged_in": logged_in,
        "claims_present": present,
        "session_identifier_present": present["sid"],
        "hf53_auth_ready": configured and logged_in and all(present.values()),
    }


def render(st: Any) -> None:
    """Página somente diagnóstica, sem leitura/gravação no Supabase."""
    st.title("AlphaFest HF65.24.53 — Homologação de login")
    st.caption("Tela isolada de teste, não integrada ao Manager em produção.")
    status = oidc_readiness(st)
    if not status["oidc_configured"]:
        st.warning("OIDC ainda não configurado para este app. Confira Secrets do ambiente de homologação.")
        return
    if not status["logged_in"]:
        st.info("Autenticação necessária para conferir identidade.")
        if st.button("Entrar com provedor OIDC"):
            st.login()
        return
    st.success("Sessão autenticada no Streamlit.")
    if st.button("Sair deste app de homologação"):
        st.logout()
        return
    # Mostrar apenas presença de campos, jamais os valores.
    st.write({
        "Identificador do provedor presente": status["claims_present"]["sub"],
        "Emissor presente": status["claims_present"]["iss"],
        "Aplicativo/audiência presente": status["claims_present"]["aud"],
        "Data de emissão presente": status["claims_present"]["iat"],
        "Data de expiração presente": status["claims_present"]["exp"],
        "Identificador de sessão revogável presente": status["claims_present"]["sid"],
    })
    if not status["session_identifier_present"]:
        st.warning(
            "O provedor não retornou sid. A HF65.24.53 exige sessão revogável; "
            "não será liberada apenas pela identidade OIDC."
        )
    elif status["hf53_auth_ready"]:
        st.info(
            "Claims mínimos presentes. A validação de revogação e ACL no servidor "
            "ainda é obrigatória; esta tela NÃO habilita acesso a dados."
        )


if __name__ == "__main__":
    import streamlit as st
    st.set_page_config(page_title="AlphaFest HF53 — Login homologação")
    render(st)
