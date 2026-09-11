"""Interface isolada do Alpha Connect Pro.

HF28: move a tela de diagnóstico das integrações para fora do app.py sem mudar
regras, credenciais, persistência ou comportamento dos testes de conexão.
"""
from __future__ import annotations

import os
from typing import Any, Callable

import requests
import streamlit as st


def _secret_value(name: str) -> str:
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = os.getenv(name, "")
    return str(value or "").strip()


def _secret_configured(name: str) -> bool:
    return bool(_secret_value(name))


def _integration_status(key: str, name: str, required: list[str], note: str = "", optional: list[str] | None = None) -> dict[str, Any]:
    present = [field for field in required if _secret_configured(field)]
    optional = optional or []
    total = len(required)
    if total and len(present) == total:
        status, icon = "Configurado", "🟢"
    elif present:
        status, icon = "Incompleto", "🟡"
    else:
        status, icon = "Não configurado", "⚪"
    return {
        "chave": key,
        "nome": name,
        "status": status,
        "icone": icon,
        "detalhe": note,
        "faltando": [field for field in required if field not in present],
        "opcionais_faltando": [field for field in optional if not _secret_configured(field)],
    }


def _test_integration(key: str, *, openai_class: Callable[[], Any] | None = None) -> tuple[bool, str]:
    """Executa o mesmo teste leve do HF27, sem publicar ou alterar dados externos."""
    try:
        if key == "openai":
            OpenAI = openai_class() if openai_class else None
            if OpenAI is None:
                return False, "Biblioteca OpenAI não instalada."
            client = OpenAI(api_key=_secret_value("OPENAI_API_KEY"))
            models = client.models.list()
            return True, f"Conexão confirmada. {len(list(models.data))} modelo(s) acessível(is)."
        if key == "meta":
            page_id, token = _secret_value("META_PAGE_ID"), _secret_value("META_ACCESS_TOKEN")
            response = requests.get(
                f"https://graph.facebook.com/v21.0/{page_id}",
                params={"fields": "id,name", "access_token": token},
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            return True, f"Página conectada: {data.get('name', data.get('id', 'Meta'))}."
        if key == "instagram":
            account, token = _secret_value("INSTAGRAM_ACCOUNT_ID"), _secret_value("META_ACCESS_TOKEN")
            response = requests.get(
                f"https://graph.facebook.com/v21.0/{account}",
                params={"fields": "id,username,name", "access_token": token},
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            return True, f"Instagram conectado: @{data.get('username', 'conta profissional')}."
        if key == "whatsapp":
            phone_id, token = _secret_value("WHATSAPP_PHONE_NUMBER_ID"), _secret_value("META_ACCESS_TOKEN")
            response = requests.get(
                f"https://graph.facebook.com/v21.0/{phone_id}",
                params={"fields": "display_phone_number,verified_name", "access_token": token},
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            return True, f"WhatsApp conectado: {data.get('verified_name', '')} {data.get('display_phone_number', '')}.".strip()
        if key == "youtube":
            if not _secret_configured("YOUTUBE_REFRESH_TOKEN"):
                return False, "Cliente OAuth criado, mas ainda falta autorizar o canal e salvar YOUTUBE_REFRESH_TOKEN."
            payload = {
                "client_id": _secret_value("YOUTUBE_CLIENT_ID"),
                "client_secret": _secret_value("YOUTUBE_CLIENT_SECRET"),
                "refresh_token": _secret_value("YOUTUBE_REFRESH_TOKEN"),
                "grant_type": "refresh_token",
            }
            response = requests.post("https://oauth2.googleapis.com/token", data=payload, timeout=15)
            response.raise_for_status()
            return True, "OAuth do YouTube renovado com sucesso."
        if key == "tiktok":
            return False, "Credenciais básicas presentes; teste completo ficará disponível após a revisão do aplicativo TikTok."
        return False, "Integração desconhecida."
    except Exception as exc:
        message = str(exc)
        if len(message) > 240:
            message = message[:237] + "..."
        return False, message


def render_alpha_connect(
    *,
    load_document: Callable[..., Any],
    save_document: Callable[..., Any],
    integrations_file: str,
    can_execute_technical_actions: Callable[[], bool],
    user_in_protected_operation: Callable[[], bool],
    now_local: Callable[[], Any],
    current_user: Callable[[], dict[str, Any]],
    openai_class: Callable[[], Any] | None = None,
) -> None:
    """Renderiza o Alpha Connect Pro com as mesmas dependências do app original."""
    st.subheader("🔗 Alpha Connect Pro")
    st.caption("Diagnóstico seguro das integrações. Nenhuma chave secreta é exibida e os testes não publicam conteúdo.")
    integrations = [
        _integration_status("openai", "OpenAI", ["OPENAI_API_KEY"], "Textos comerciais e análise visual.", ["OPENAI_MODEL"]),
        _integration_status("meta", "Meta / Facebook", ["META_APP_ID", "META_APP_SECRET", "META_ACCESS_TOKEN", "META_PAGE_ID"], "Página e publicação pela Meta Graph API."),
        _integration_status("instagram", "Instagram", ["META_ACCESS_TOKEN", "INSTAGRAM_ACCOUNT_ID"], "Conta profissional vinculada à Página."),
        _integration_status("whatsapp", "WhatsApp Business", ["META_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_BUSINESS_ACCOUNT_ID"], "Mensagens pela plataforma oficial."),
        _integration_status("youtube", "YouTube", ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET"], "OAuth do canal para vídeos e Shorts.", ["YOUTUBE_REFRESH_TOKEN", "YOUTUBE_CHANNEL_ID"]),
        _integration_status("tiktok", "TikTok", ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET"], "Pendente até concluir a revisão do aplicativo."),
    ]

    history = load_document("integracoes_db", integrations_file, {})
    history = history if isinstance(history, dict) else {}
    cols = st.columns(2)
    for index, item in enumerate(integrations):
        with cols[index % 2].container(border=True):
            st.markdown(f"### {item['icone']} {item['nome']}")
            st.write(f"**Status:** {item['status']}")
            st.caption(item["detalhe"])
            if item["faltando"]:
                st.caption("Faltando: " + ", ".join(item["faltando"]))
            last = history.get(item["chave"], {}) if isinstance(history, dict) else {}
            if last:
                badge = "✅" if last.get("ok") else "⚠️"
                st.caption(f"{badge} Último teste: {last.get('quando', '—')} — {last.get('mensagem', '')}")
            can_test = item["status"] == "Configurado" and can_execute_technical_actions()
            if user_in_protected_operation():
                st.caption("🛡️ Testes técnicos bloqueados no modo de atendimento.")
            if st.button(
                "🧪 Testar conexão",
                key=f"teste_connect_{item['chave']}",
                use_container_width=True,
                disabled=not can_test,
            ):
                with st.spinner(f"Testando {item['nome']}..."):
                    ok, message = _test_integration(item["chave"], openai_class=openai_class)
                history[item["chave"]] = {
                    "ok": ok,
                    "mensagem": message,
                    "quando": now_local().strftime("%d/%m/%Y %H:%M"),
                    "usuario": current_user().get("nome", "Equipe"),
                }
                save_document("integracoes_db", history, integrations_file)
                (st.success if ok else st.warning)(message)
                st.rerun()
    st.info(
        "Credencial configurada não significa permissão de publicação. "
        "A publicação será habilitada somente após OAuth, permissões e teste específico do canal."
    )
