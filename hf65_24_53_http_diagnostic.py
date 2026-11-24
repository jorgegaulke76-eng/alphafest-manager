"""Diagnóstico HTTP SOMENTE LEITURA, opt-in, no app OIDC de homologação.

Sem acesso a clientes, sem mutação e sem habilitar relatório privado.
A credencial Supabase vive somente nos Secrets do servidor Streamlit.
Negar antes de qualquer HTTP se login, email verificado, allowlist ou Secrets
estiverem ausentes. Nunca exibir e-mails, tokens, segredos ou resposta bruta.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from hmac import compare_digest
from typing import Any

STAGING_URL = "https://hvaptsdhaxrdxgqqpicu.supabase.co"
GOOGLE_ISSUER = frozenset({"https://accounts.google.com", "accounts.google.com"})


def _eligible(st: Any) -> tuple[bool, str | None]:
    """Verificação auxiliar só libera probe SEM DADOS, não ACL do Manager."""
    try:
        secrets = st.secrets
        if secrets.get("HF53_HTTP_DIAG_ENABLED") is not True:
            return False, "Diagnóstico HTTP desativado."
        target = secrets.get("HF53_STAGING_SUPABASE_URL")
        key = secrets.get("HF53_STAGING_SERVICE_KEY")
        allowed = secrets.get("HF53_HTTP_DIAG_ALLOWED_EMAIL")
        if target != STAGING_URL or not isinstance(key, str) or not key.strip():
            return False, "Conexão exclusiva de homologação ainda não configurada."
        if not isinstance(allowed, str) or not allowed.strip():
            return False, "Lista de acesso ao diagnóstico ainda não configurada."
        user = st.user
        if user.is_logged_in is not True:
            return False, "Login Google obrigatório."
        claims = user.to_dict()
        if not isinstance(claims, Mapping):
            return False, "Identidade não confirmada."
        email = claims.get("email")
        if (claims.get("iss") not in GOOGLE_ISSUER
            or claims.get("email_verified") is not True
            or not isinstance(email, str)
            or not compare_digest(email.casefold().encode("utf-8"),
                                  allowed.strip().casefold().encode("utf-8"))):
            return False, "Operador não autorizado para o diagnóstico."
        now = datetime.now(timezone.utc).timestamp()
        if (isinstance(claims.get("exp"), bool)
            or not isinstance(claims.get("exp"), (int, float))
            or not now < claims["exp"]):
            return False, "Sessão expirada."
        return True, None
    except Exception:
        return False, "Verificação de acesso ao diagnóstico indisponível."


def render_http_diagnostic(st: Any, *, probe: Callable[..., str] | None = None) -> None:
    """Exibe apenas botão de GET aleatório quando login + allowlist aprovados."""
    st.subheader("Conexão HTTP de homologação — leitura de teste")
    authorized, reason = _eligible(st)
    if not authorized:
        st.caption(reason or "Diagnóstico não disponível.")
        return
    st.caption("Consulta uma chave aleatória inexistente. Não lê pedidos nem grava dados.")
    if not st.button("Testar conexão privada de homologação"):
        return
    try:
        if probe is None:
            from scripts.hf65_24_53_staging_http_probe import run_probe
            probe = run_probe
        # Segredos nunca passam para a interface nem para mensagens.
        result = probe(
            base_url=st.secrets["HF53_STAGING_SUPABASE_URL"],
            service_key=st.secrets["HF53_STAGING_SERVICE_KEY"],
            write_enabled=False,
        )
        if result != "Leitura HTTP privada de homologação confirmada; nenhuma escrita.":
            raise ValueError("Resposta de teste não confirmada.")
    except Exception:
        st.error("Conexão privada não confirmada. Confira configurações no servidor.")
        return
    st.success("GET privado de homologação confirmado, sem escrita nem dados de clientes.")


def render_session_write_diagnostic(
    st: Any, *, probe: Callable[..., str] | None = None,
) -> None:
    """POST/GET/PATCH exclusivamente de uma sessao ficticia de 60 s.

    NAO e o login do Manager e nao concede permissao ao relatorio.
    """
    st.subheader("Sessao de teste — criacao e revogacao HTTP")
    authorized, reason = _eligible(st)
    if not authorized:
        st.caption(reason or "Diagnostico indisponivel.")
        return
    try:
        enabled = st.secrets.get("HF53_SESSION_WRITE_DIAG_ENABLED") is True
    except Exception:
        enabled = False
    if not enabled:
        st.caption("Ensaio de escrita de sessao desativado.")
        return
    st.caption(
        "Cria uma sessao ficticia de 60 segundos, verifica e revoga. "
        "Uma linha revogada permanece no banco de homologacao para auditoria."
    )
    if not st.button("Testar criacao e revogacao HTTP de sessao"):
        return
    try:
        if probe is None:
            from hf65_24_53_session_write_probe import run_session_write_probe
            probe = run_session_write_probe
        result = probe(
            base_url=st.secrets["HF53_STAGING_SUPABASE_URL"],
            service_key=st.secrets["HF53_STAGING_SERVICE_KEY"],
        )
        from hf65_24_53_session_write_probe import SUCCESS
        if result != SUCCESS:
            raise ValueError("Ensaio sem confirmacao.")
    except Exception:
        st.error(
            "Teste de criacao/revogacao nao confirmado. "
            "Nenhum acesso comercial foi habilitado."
        )
        return
    st.success(
        "POST, GET e PATCH confirmados: sessao ficticia revogada. "
        "Relatorio comercial continua bloqueado."
    )
