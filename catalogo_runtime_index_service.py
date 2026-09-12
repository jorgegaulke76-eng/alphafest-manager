"""Índices leves de leitura para o Catálogo AlphaFest.

HF31: reduz reconstruções repetidas da busca/edição rápida e consolida as
estatísticas históricas do Catálogo em uma única passagem pelo Histórico.
Este módulo é somente leitura: não grava, não exclui e não altera produtos.
"""
from __future__ import annotations

from typing import Any, Callable


def _as_text(value: Any) -> str:
    return str(value or "")


def build_catalog_view_index(
    catalogo: list[dict[str, Any]] | None,
    *,
    normalize: Callable[[Any], str],
) -> dict[str, Any]:
    """Pré-calcula campos usados repetidamente pela aba Produtos.

    Mantém os mesmos critérios já usados no app: a busca rápida considera
    nome/categoria/subcategoria; a busca completa inclui os campos editoriais,
    aliases, variações e arquivos da Biblioteca.
    """
    rows: list[dict[str, Any]] = []
    categories: set[str] = set()
    campaigns: set[str] = set()

    ignored_campaigns = {
        "permanente / todas as épocas",
        "permanente",
        "todas as épocas",
    }

    for idx, raw in enumerate(catalogo or []):
        p = raw or {}
        nome = _as_text(p.get("Nome") or "Produto")
        categoria = _as_text(p.get("Categoria")).strip()
        subcategoria = _as_text(p.get("Subcategoria")).strip()

        if categoria:
            categories.add(categoria)

        campanhas_norm: list[str] = []
        for camp in p.get("CampanhasPermitidas") or []:
            camp_txt = _as_text(camp).strip()
            if not camp_txt:
                continue
            camp_cf = camp_txt.casefold()
            campanhas_norm.append(normalize(camp_txt))
            if camp_cf not in ignored_campaigns:
                campaigns.add(camp_txt)

        aliases = " ".join(_as_text(x) for x in (p.get("Aliases") or []))
        variacoes = " ".join(_as_text(x) for x in (p.get("Variacoes") or []))
        arquivos_parts: list[str] = []
        for a in p.get("ArquivosBiblioteca") or []:
            if not isinstance(a, dict):
                continue
            tags = " ".join(_as_text(t) for t in (a.get("tags") or []))
            arquivos_parts.append(
                f"{_as_text(a.get('nome'))} {_as_text(a.get('descricao'))} {tags}"
            )

        quick_haystack = f"{nome} {categoria} {subcategoria}".casefold()
        full_haystack = (
            f"{_as_text(p.get('Nome'))} {_as_text(p.get('Categoria'))} "
            f"{_as_text(p.get('Subcategoria'))} {_as_text(p.get('CodigoInterno'))} "
            f"{_as_text(p.get('Descricao'))} {_as_text(p.get('PalavrasChave'))} "
            f"{aliases} {variacoes} " + " ".join(arquivos_parts)
        ).lower()

        rows.append({
            "index": idx,
            "sort_key": normalize(p.get("Nome", "")),
            "quick_haystack": quick_haystack,
            "full_haystack": full_haystack,
            "category": categoria,
            "campaigns_normalized": tuple(campanhas_norm),
        })

    rows_sorted = sorted(rows, key=lambda row: row["sort_key"])
    return {
        "rows": rows,
        "rows_sorted": rows_sorted,
        "categories": sorted(categories, key=normalize),
        "campaigns": sorted(campaigns, key=normalize),
    }


def filter_quick_indices(
    view_index: dict[str, Any],
    *,
    search: str = "",
    category: str = "Todas",
) -> list[int]:
    term = _as_text(search).strip().casefold()
    chosen_category = _as_text(category)
    result: list[int] = []
    for row in view_index.get("rows") or []:
        if term and term not in _as_text(row.get("quick_haystack")):
            continue
        if chosen_category != "Todas" and _as_text(row.get("category")) != chosen_category:
            continue
        result.append(int(row["index"]))
    return result


def filter_full_indices(view_index: dict[str, Any], search: str = "") -> list[int]:
    term = _as_text(search).strip().lower()
    result: list[int] = []
    for row in view_index.get("rows_sorted") or []:
        if term and term not in _as_text(row.get("full_haystack")):
            continue
        result.append(int(row["index"]))
    return result


def build_history_stats(
    catalogo: list[dict[str, Any]] | None,
    historico: list[dict[str, Any]] | None,
    *,
    resolve_official_name: Callable[[Any, list[dict[str, Any]]], str],
    normalize: Callable[[Any], str],
    value_float: Callable[[Any], float],
) -> dict[str, dict[str, Any]]:
    """Consolida o histórico por produto oficial em uma única passagem.

    A implementação anterior varria o Histórico inteiro para cada produto
    mostrado na lista. Aqui cada item histórico é resolvido no máximo uma vez
    por nome bruto repetido, preservando a mesma regra oficial de resolução.
    """
    cat = list(catalogo or [])
    stats: dict[str, dict[str, Any]] = {}
    resolved_names: dict[str, str] = {}

    for proposta in historico or []:
        data_geracao = _as_text((proposta or {}).get("data_geracao") or "—")
        for item in (proposta or {}).get("itens") or []:
            bruto = _as_text((item or {}).get("produto"))
            cache_key = bruto
            if cache_key not in resolved_names:
                resolved_names[cache_key] = _as_text(resolve_official_name(bruto, cat))
            oficial = resolved_names[cache_key]
            key = normalize(oficial)
            if not key:
                continue

            entry = stats.setdefault(
                key,
                {"quantidade": 0.0, "valor": 0.0, "ultima_ocorrencia": "—"},
            )
            qtd = value_float((item or {}).get("quantidade", 0))
            unit = value_float((item or {}).get("valor_unitario", 0))
            entry["quantidade"] += qtd
            entry["valor"] += qtd * unit
            # Preserva a semântica anterior: primeira ocorrência encontrada na
            # ordem atual do Histórico é a exibida como "Última ocorrência".
            if entry["ultima_ocorrencia"] == "—":
                entry["ultima_ocorrencia"] = data_geracao

    return stats


def paginate_indices(indices: list[int] | None, *, page: int = 1, page_size: int | None = 24) -> dict[str, Any]:
    """Recorta uma lista de índices para renderização paginada.

    Não altera busca nem ordenação; apenas reduz a quantidade de cartões que o
    Streamlit precisa construir por rerun. ``page_size=None`` mantém todos.
    """
    values = [int(x) for x in (indices or [])]
    total = len(values)
    if page_size is None or int(page_size or 0) <= 0:
        return {
            "indices": values, "total": total, "page": 1, "pages": 1 if total else 0,
            "page_size": None, "start": 0, "end": total,
        }
    size = max(1, int(page_size))
    pages = max(1, (total + size - 1) // size) if total else 0
    current = min(max(1, int(page or 1)), pages or 1)
    start = (current - 1) * size if total else 0
    end = min(total, start + size)
    return {
        "indices": values[start:end], "total": total, "page": current,
        "pages": pages, "page_size": size, "start": start, "end": end,
    }
