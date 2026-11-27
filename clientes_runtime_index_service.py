"""Índices leves de leitura para Clientes/Relacionamentos do AlphaFest Manager.

HF33: evita varrer o Histórico inteiro uma vez por cliente na tela Clientes 360.
Este módulo é puro e somente leitura: não grava, não consolida e não modifica
cadastros, propostas ou vínculos.
"""
from __future__ import annotations

from typing import Any, Callable


def build_client_proposals_index(
    historico: list[dict[str, Any]] | None,
    *,
    client_key: Callable[[Any, Any, Any], str],
) -> dict[str, Any]:
    """Indexa propostas pela posição original, relacionamento_id e chave legada.

    Guardar posições permite reproduzir exatamente a ordem do Histórico e unir
    vínculo atual + fallback legado sem duplicar a mesma proposta.
    """
    items = [p for p in (historico or []) if isinstance(p, dict)]
    by_relationship: dict[str, list[int]] = {}
    by_legacy_key: dict[str, list[int]] = {}

    for pos, prop in enumerate(items):
        rel_id = str(prop.get("relacionamento_id", "") or "").strip()
        if rel_id:
            by_relationship.setdefault(rel_id, []).append(pos)

        legacy_key = client_key(
            prop.get("cliente_nome", prop.get("cliente", "")),
            prop.get("documento", prop.get("cliente_cpf_cnpj", "")),
            prop.get("whatsapp", prop.get("cliente_wa", "")),
        )
        if legacy_key:
            by_legacy_key.setdefault(str(legacy_key), []).append(pos)

    return {
        "items": items,
        "by_relationship": by_relationship,
        "by_legacy_key": by_legacy_key,
        "history_size": len(items),
    }


def proposals_for_client(
    cliente: dict[str, Any] | None,
    index: dict[str, Any] | None,
    *,
    client_key: Callable[[Any, Any, Any], str],
) -> list[dict[str, Any]]:
    """Retorna as mesmas propostas da regra histórica, usando o índice.

    A regra original aceita proposta por ``relacionamento_id`` e também por
    chave legada do contato. A união por posição preserva a ordem original e
    garante que uma proposta que satisfaça os dois critérios apareça uma vez.
    """
    cliente = cliente or {}
    index = index or {}
    items = index.get("items") or []
    by_relationship = index.get("by_relationship") or {}
    by_legacy_key = index.get("by_legacy_key") or {}

    rel_id = str(cliente.get("id", "") or "").strip()
    legacy_key = client_key(
        cliente.get("nome", ""),
        cliente.get("documento", ""),
        cliente.get("whatsapp", ""),
    )

    positions: set[int] = set()
    if rel_id:
        positions.update(int(p) for p in by_relationship.get(rel_id, []))
    if legacy_key:
        positions.update(int(p) for p in by_legacy_key.get(str(legacy_key), []))

    return [items[pos] for pos in sorted(positions) if 0 <= pos < len(items)]
