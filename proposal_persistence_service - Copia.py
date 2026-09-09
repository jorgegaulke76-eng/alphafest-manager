"""20.4.9-I8.13.5-HF3 — persistência segura e desacoplada de propostas.

O módulo não conhece Streamlit, session_state nem Supabase. O orquestrador injeta
as funções de leitura/gravação. A regra central é: uma proposta só é considerada
alterada depois da confirmação da camada de persistência.
"""
from __future__ import annotations

from typing import Any, Callable


def atualizar_proposta_fresca(
    numero: Any,
    updater: Callable[[dict[str, Any]], Any],
    *,
    cloud_mutate: Callable[..., Any] | None = None,
    load_fresh: Callable[[], list[dict[str, Any]]] | None = None,
    save_full: Callable[[list[dict[str, Any]]], bool] | None = None,
    on_cloud_document: Callable[[list[dict[str, Any]]], Any] | None = None,
    invalidate: Callable[[], Any] | None = None,
    document_key: str = "historico_orcamentos",
    local_file: str = "historico_orcamentos.json",
    retries: int = 4,
) -> tuple[bool, dict[str, Any] | None, str]:
    """Altera um único registro usando CAS quando disponível e fallback fresco.

    ``cloud_mutate`` deve seguir o contrato já usado pelo Manager:
    ``(key, local_file, default, id_field, id_value, updater, retries=N)`` e
    retornar ``(ok, atualizado, documento, motivo)``.
    """
    numero_txt = str(numero or "").strip()
    if not numero_txt:
        return False, None, "Número da proposta não informado."
    if not callable(updater):
        return False, None, "Atualizador da proposta não informado."

    if callable(cloud_mutate):
        ok, atualizado, documento, motivo = cloud_mutate(
            document_key,
            local_file,
            [],
            "numero_proposta",
            numero_txt,
            updater,
            retries=retries,
        )
        if callable(invalidate):
            invalidate()
        if ok and isinstance(documento, list) and callable(on_cloud_document):
            on_cloud_document(documento)
        return bool(ok), atualizado if isinstance(atualizado, dict) else atualizado, str(motivo or "")

    if not callable(load_fresh) or not callable(save_full):
        return False, None, "Camada de persistência indisponível."

    historico = load_fresh()
    if not isinstance(historico, list):
        return False, None, "Histórico inválido após leitura fresca."
    alvo = next(
        (p for p in historico if isinstance(p, dict) and str(p.get("numero_proposta") or "").strip() == numero_txt),
        None,
    )
    if alvo is None:
        return False, None, "Proposta não encontrada no histórico."

    updater(alvo)
    ok = bool(save_full(historico))
    if callable(invalidate):
        invalidate()
    return ok, alvo, "fallback"
