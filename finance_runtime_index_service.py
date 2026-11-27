"""Índices leves para o faturamento/financeiro do AlphaFest Manager.

HF39: preserva a precedência histórica de resolução de relacionamento e evita
varreduras lineares repetidas da base de Clientes durante o faturamento mensal.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from relacionamentos_service import digitos, normalizar_texto_cliente, telefone_chave


@dataclass(frozen=True)
class FinanceClientIndex:
    clientes: tuple[dict[str, Any], ...]
    by_id: dict[str, dict[str, Any]]
    by_doc: dict[str, dict[str, Any]]
    by_wa: dict[str, tuple[int, dict[str, Any]]]
    by_name: dict[str, tuple[int, dict[str, Any]]]


def _set_first(mapping: dict, key, value) -> None:
    if key and key not in mapping:
        mapping[key] = value


def build_finance_client_index(clientes: Iterable[dict[str, Any]] | None) -> FinanceClientIndex:
    """Cria índices sem alterar a ordem/precedência da base original."""
    lista = tuple(c for c in (clientes or []) if isinstance(c, dict))
    by_id: dict[str, dict[str, Any]] = {}
    by_doc: dict[str, dict[str, Any]] = {}
    by_wa: dict[str, tuple[int, dict[str, Any]]] = {}
    by_name: dict[str, tuple[int, dict[str, Any]]] = {}

    for idx, cli in enumerate(lista):
        cid = str(cli.get("id", "") or "").strip()
        doc = digitos(cli.get("documento"))
        wa = telefone_chave(cli.get("whatsapp"))
        nome = normalizar_texto_cliente(cli.get("nome")).casefold()
        _set_first(by_id, cid, cli)
        _set_first(by_doc, doc, cli)
        _set_first(by_wa, wa, (idx, cli))
        _set_first(by_name, nome, (idx, cli))

    return FinanceClientIndex(
        clientes=lista,
        by_id=by_id,
        by_doc=by_doc,
        by_wa=by_wa,
        by_name=by_name,
    )


def resolve_relationship_client(index: FinanceClientIndex, proposta: dict[str, Any] | None) -> dict[str, Any] | None:
    """Replica `relacionamento_da_proposta` com índice O(1).

    A rotina histórica, após relacionamento_id, percorre Clientes na ordem e
    retorna o primeiro registro cujo WhatsApp OU nome combina. Para manter isso
    exatamente, comparamos a posição do primeiro match de cada chave.
    """
    proposta = proposta or {}
    rel_id = str(proposta.get("relacionamento_id", "") or "").strip()
    if rel_id:
        achado = index.by_id.get(rel_id)
        if achado is not None:
            return achado

    wa = telefone_chave(proposta.get("whatsapp", proposta.get("cliente_wa", "")))
    nome = normalizar_texto_cliente(
        proposta.get("cliente_nome", proposta.get("cliente", ""))
    ).casefold()

    wa_match = index.by_wa.get(wa) if wa else None
    nome_match = index.by_name.get(nome) if nome else None
    if wa_match is None:
        return nome_match[1] if nome_match else None
    if nome_match is None:
        return wa_match[1]
    return wa_match[1] if wa_match[0] <= nome_match[0] else nome_match[1]


def resolve_commercial_client(index: FinanceClientIndex, proposta: dict[str, Any] | None) -> dict[str, Any] | None:
    """Replica a precedência de `localizar_cliente_comercial`: doc → WA → nome."""
    proposta = proposta or {}
    doc = digitos(proposta.get("documento", proposta.get("cliente_cpf_cnpj", "")))
    if doc and doc in index.by_doc:
        return index.by_doc[doc]

    wa = telefone_chave(proposta.get("whatsapp", proposta.get("cliente_wa", "")))
    if wa and wa in index.by_wa:
        return index.by_wa[wa][1]

    nome = normalizar_texto_cliente(
        proposta.get("cliente_nome", proposta.get("cliente", ""))
    ).casefold()
    if nome and nome in index.by_name:
        return index.by_name[nome][1]
    return None


def resolve_billing_client(index: FinanceClientIndex, proposta: dict[str, Any] | None) -> dict[str, Any] | None:
    """Resolve cliente do faturamento mensal com a mesma sequência histórica."""
    return resolve_relationship_client(index, proposta) or resolve_commercial_client(index, proposta)
