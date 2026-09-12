"""Índices de leitura para Compras / Estoque do AlphaFest Manager.

HF44: concentra consultas derivadas que antes percorriam o histórico de compras
repetidamente. Não grava dados e não altera regras comerciais/operacionais.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable, Iterable


DateParser = Callable[[Any], date]
ItemKey = Callable[[Any], str]


@dataclass
class PurchaseRuntimeIndex:
    previous_by_object: dict[int, dict]
    latest_by_group: dict[tuple[str, str, str], dict]
    last_cost_by_material_id: dict[str, dict]


def _unit(value: Any) -> str:
    return str(value or "").strip().casefold()


def _supplier(value: Any) -> str:
    return str(value or "")


def _created(value: Any) -> str:
    return str(value or "")


def _purchase_group(compra: dict, item_key: ItemKey) -> tuple[str, str, str]:
    return (
        _supplier(compra.get("fornecedor_id")),
        item_key(compra.get("item", "")),
        _unit(compra.get("unidade")),
    )


def _final_active_material_id(materials_by_id: dict[str, dict], material_id: str) -> str:
    current = str(material_id or "").strip()
    seen: set[str] = set()
    while current and current not in seen:
        seen.add(current)
        mat = materials_by_id.get(current)
        if not mat:
            return ""
        if mat.get("ativo", True):
            return current
        current = str(mat.get("consolidado_para_id") or "").strip()
    return ""


def build_purchase_runtime_index(
    compras: Iterable[dict] | None,
    estoque: dict | None,
    *,
    item_key: ItemKey,
    date_parser: DateParser,
) -> PurchaseRuntimeIndex:
    """Cria índices equivalentes às consultas históricas do app.

    * ``previous_by_object`` preserva a noção de compra anterior considerando
      fornecedor + item normalizado + unidade e a ordenação data/criado_em.
    * ``last_cost_by_material_id`` preserva custos de materiais consolidados e
      compras legadas sem ``material_estoque_id``.
    """
    purchases = [p for p in (compras or []) if isinstance(p, dict)]

    grouped: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for compra in purchases:
        grouped[_purchase_group(compra, item_key)].append(compra)

    previous_by_object: dict[int, dict] = {}
    latest_by_group: dict[tuple[str, str, str], dict] = {}
    for group_key, group in grouped.items():
        ordered = sorted(
            group,
            key=lambda c: (date_parser(c.get("data_compra")), _created(c.get("criado_em"))),
        )
        previous: dict | None = None
        previous_sort_key: tuple[date, str] | None = None
        for compra in ordered:
            sort_key = (date_parser(compra.get("data_compra")), _created(compra.get("criado_em")))
            # A regra antiga exige estritamente data/criado anterior. Se houver
            # empate exato, nenhuma das compras empatadas enxerga a outra.
            if previous is not None and previous_sort_key is not None and previous_sort_key < sort_key:
                previous_by_object[id(compra)] = previous
            # Para o próximo item, mantenha a compra mais recente do último
            # sort_key estritamente menor. Em empates, a escolha antiga não é
            # observável como "anterior" para as próprias empatadas.
            if previous_sort_key is None or sort_key > previous_sort_key:
                previous = compra
                previous_sort_key = sort_key
            elif sort_key == previous_sort_key:
                # A busca antiga, quando usada sem ``antes_de``, escolhe o último
                # elemento após sort estável reverso. O primeiro do empate no input
                # prevalece. Não substituímos aqui para preservar isso.
                pass
        if ordered:
            # Equivalente à ordenação reverse=True do app: em empate, o primeiro
            # item original do grupo prevalece por estabilidade do sort.
            latest_by_group[group_key] = sorted(
                group,
                key=lambda c: (date_parser(c.get("data_compra")), _created(c.get("criado_em"))),
                reverse=True,
            )[0]

    # Índice de último custo por material ativo, incluindo nomes/IDs de materiais
    # antigos consolidados para o material atual.
    estoque = estoque or {}
    materials = [m for m in (estoque.get("materiais") or []) if isinstance(m, dict)]
    materials_by_id = {str(m.get("id") or ""): m for m in materials if str(m.get("id") or "")}

    alias_ids_by_final: dict[str, set[str]] = defaultdict(set)
    alias_names_by_final: dict[str, set[str]] = defaultdict(set)
    unit_by_final: dict[str, str] = {}
    active_ids: set[str] = set()

    for mat in materials:
        mid = str(mat.get("id") or "").strip()
        if not mid:
            continue
        final_id = _final_active_material_id(materials_by_id, mid)
        if not final_id:
            continue
        final = materials_by_id.get(final_id) or {}
        if final.get("ativo", True):
            active_ids.add(final_id)
            alias_ids_by_final[final_id].add(mid)
            name_key = item_key(mat.get("nome"))
            if name_key:
                alias_names_by_final[final_id].add(name_key)
            unit_by_final[final_id] = _unit(final.get("unidade"))

    # Uma chave legada pode corresponder a mais de um material ativo; a função
    # antiga também permitiria que a mesma compra sem ID fosse candidata a ambos.
    finals_by_legacy_name_unit: dict[tuple[str, str], set[str]] = defaultdict(set)
    final_by_any_material_id: dict[str, str] = {}
    for final_id in active_ids:
        for alias_id in alias_ids_by_final.get(final_id, set()):
            final_by_any_material_id[alias_id] = final_id
        for name_key in alias_names_by_final.get(final_id, set()):
            finals_by_legacy_name_unit[(unit_by_final.get(final_id, ""), name_key)].add(final_id)

    last_candidates: dict[str, tuple[date, str, dict]] = {}
    for compra in purchases:
        unit = _unit(compra.get("unidade"))
        compra_mid = str(compra.get("material_estoque_id") or "").strip()
        targets: set[str] = set()
        if compra_mid:
            final_id = final_by_any_material_id.get(compra_mid, "")
            if final_id and unit == unit_by_final.get(final_id, ""):
                targets.add(final_id)
        else:
            targets.update(finals_by_legacy_name_unit.get((unit, item_key(compra.get("item"))), set()))
        if not targets:
            continue
        sort_key = (date_parser(compra.get("data_compra")), _created(compra.get("criado_em")))
        for final_id in targets:
            current = last_candidates.get(final_id)
            if current is None or sort_key > (current[0], current[1]):
                last_candidates[final_id] = (sort_key[0], sort_key[1], compra)
            # Em empate exato, a função antiga usa sort(reverse=True) estável e
            # portanto preserva o primeiro candidato encontrado.

    return PurchaseRuntimeIndex(
        previous_by_object=previous_by_object,
        latest_by_group=latest_by_group,
        last_cost_by_material_id={mid: reg[2] for mid, reg in last_candidates.items()},
    )


def previous_purchase(
    index: PurchaseRuntimeIndex,
    compra: dict,
) -> dict | None:
    return index.previous_by_object.get(id(compra))


def latest_purchase_for_group(
    index: PurchaseRuntimeIndex,
    fornecedor_id: Any,
    item: Any,
    unidade: Any,
    *,
    item_key: ItemKey,
) -> dict | None:
    return index.latest_by_group.get((_supplier(fornecedor_id), item_key(item), _unit(unidade)))


def last_cost_for_material(index: PurchaseRuntimeIndex, material_id: Any) -> dict | None:
    return index.last_cost_by_material_id.get(str(material_id or "").strip())
