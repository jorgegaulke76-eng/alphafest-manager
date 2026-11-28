"""HF53: composição privada exclusivamente de HOMOLOGAÇÃO (sem UI).

Login Google OIDC + sessão de trabalho revogável + ACL comercial separada
são conferidos antes de ler o diário privado. Somente então os dois snapshots
do Manager são carregados via PostgREST de homologação e saneados. Falha
fechado se qualquer documento estiver ausente; NÃO usa JSON local.
Não importado por app.py ou pela tela de diagnóstico.
"""
from __future__ import annotations

from typing import Any

from commercial_server_acl_config import commercial_read_policy_from_server_secrets
from commercial_work_session_gate import _backend
from commercial_work_session_report_bridge import build_work_session_commercial_report
from commercial_staging_official_reader import read_sanitized_staging_official_snapshots
from commercial_private_document_adapter import PrivateStoreDenied


def build_integrated_staging_commercial_report(
    *, st: Any, cloud: Any, http: Any,
) -> dict[str, Any]:
    """Permissão READ nunca é derivada do email do diagnóstico."""
    try:
        policy = commercial_read_policy_from_server_secrets(st)
        if not callable(getattr(http, "get", None)):
            raise ValueError()
        # O diário de atribuições também precisa vir EXATAMENTE do staging.
        # Não basta conferir o host das propostas: o cloud pode ter sido
        # inicializado com credencial de outro projeto.
        url, headers = _backend(st)
        from commercial_bootstrap_postgrest_contract import _validate_args
        from commercial_private_document_adapter import DOCUMENT_KEY
        if (not callable(getattr(cloud, "_config", None))
            or not callable(getattr(cloud, "_headers", None))):
            raise ValueError()
        cloud_url, _ = cloud._config()
        cloud_headers = cloud._headers()
        _validate_args(cloud_url, cloud_headers, DOCUMENT_KEY)
        if cloud_url.rstrip("/") != url or cloud_headers.get("apikey") != headers["apikey"]:
            raise ValueError()
    except Exception:
        raise PrivateStoreDenied("Leitura comercial de homologacao indisponivel.") from None

    def official_snapshots():
        # Chamado somente APÓS autenticação, sessão ativa e ACL por operação
        # no bridge autorizado. Sem cache nem snapshot substituto.
        url, headers = _backend(st)
        return read_sanitized_staging_official_snapshots(
            get=http.get, base_url=url, headers=headers,
        )

    return build_work_session_commercial_report(
        st=st, policy=policy, cloud=cloud,
        get_session=http.get,
        load_official_snapshots=official_snapshots,
    )
