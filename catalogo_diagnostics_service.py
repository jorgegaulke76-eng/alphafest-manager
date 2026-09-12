"""Diagnóstico leve do Catálogo Oficial.

HF30: concentra a detecção de possíveis duplicidades fora do ``app.py`` e evita
recalcular o mesmo cruzamento enquanto Nome/Aliases/Revisões não mudarem.

O módulo é somente leitura: nunca une, apaga ou altera produtos.
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from itertools import combinations
from typing import Any

from catalogo_orcamento_service import normalizar_identidade_produto


def nome_flexivel(nome: Any) -> str:
    """Normalização conservadora usada apenas como sinal de possível duplicidade."""
    texto = unicodedata.normalize("NFKD", str(nome or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c)).casefold()
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    palavras = [
        p for p in texto.split()
        if p not in {"de", "do", "da", "dos", "das", "para", "com"}
    ]
    return " ".join(palavras).strip()


def chave_duplicidade(nome_a: Any, nome_b: Any) -> str:
    nomes = sorted([
        normalizar_identidade_produto(nome_a),
        normalizar_identidade_produto(nome_b),
    ])
    return "duplicidade:" + "|".join(nomes)


def _revisoes_ativas(produto: dict[str, Any]) -> set[str]:
    ultimas: dict[str, dict[str, Any]] = {}
    for reg in list((produto or {}).get("RevisoesSaneamentoTHU", []) or []):
        if not isinstance(reg, dict):
            continue
        chave = str(reg.get("chave_alerta") or "").strip()
        if chave:
            ultimas[chave] = reg
    return {
        chave
        for chave, reg in ultimas.items()
        if str(reg.get("decisao") or "") in {
            "aceito_como_esta",
            "nao_se_aplica",
            "nao_sao_duplicados",
        }
    }


def _aliases(produto: dict[str, Any]) -> set[str]:
    raw = (produto or {}).get("Aliases", []) or []
    if isinstance(raw, str):
        raw = [raw]
    return {
        normalizar_identidade_produto(x)
        for x in raw
        if str(x).strip()
    }


def _signature_payload(catalogo: list[dict[str, Any]]) -> str:
    """Serializa somente campos que afetam a detecção de duplicidade."""
    slim = []
    for produto in catalogo:
        produto = produto or {}
        slim.append({
            "Nome": str(produto.get("Nome") or ""),
            "Aliases": list(produto.get("Aliases") or []) if not isinstance(produto.get("Aliases"), str) else [produto.get("Aliases")],
            "RevisoesSaneamentoTHU": [
                {
                    "chave_alerta": str((r or {}).get("chave_alerta") or ""),
                    "decisao": str((r or {}).get("decisao") or ""),
                }
                for r in list(produto.get("RevisoesSaneamentoTHU", []) or [])
                if isinstance(r, dict)
            ],
        })
    return json.dumps(slim, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _pair(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def _prefer(existing: tuple[str, str] | None, motivo: str, nivel: str) -> tuple[str, str]:
    """Mantém a mesma precedência do algoritmo histórico: estrita > alias > flex."""
    rank = {"forte_nome": 3, "forte_alias": 2, "provavel": 1}
    current_key = None
    if existing:
        if existing[0] == "Mesmo nome após normalização":
            current_key = "forte_nome"
        elif existing[0] == "Nome de um cadastro aparece como alias do outro":
            current_key = "forte_alias"
        else:
            current_key = "provavel"
    new_key = (
        "forte_nome" if motivo == "Mesmo nome após normalização"
        else "forte_alias" if motivo == "Nome de um cadastro aparece como alias do outro"
        else "provavel"
    )
    if existing is None or rank[new_key] > rank.get(current_key or "", 0):
        return (motivo, nivel)
    return existing


@lru_cache(maxsize=24)
def _possiveis_duplicidades_cached(payload: str) -> tuple[tuple[Any, ...], ...]:
    catalogo = json.loads(payload)
    n = len(catalogo)

    strict_names: list[str] = []
    flex_names: list[str] = []
    aliases: list[set[str]] = []
    accepted: list[set[str]] = []
    nomes: list[str] = []

    strict_index: dict[str, list[int]] = {}
    flex_index: dict[str, list[int]] = {}

    for idx, produto in enumerate(catalogo):
        produto = produto or {}
        nome = str(produto.get("Nome") or "").strip()
        nomes.append(nome)
        estrita = normalizar_identidade_produto(nome) if nome else ""
        flex = nome_flexivel(nome) if nome else ""
        strict_names.append(estrita)
        flex_names.append(flex)
        aliases.append(_aliases(produto))
        accepted.append(_revisoes_ativas(produto))
        if estrita:
            strict_index.setdefault(estrita, []).append(idx)
        if flex:
            flex_index.setdefault(flex, []).append(idx)

    candidates: dict[tuple[int, int], tuple[str, str]] = {}

    # 1) Mesmo nome normalizado.
    for indices in strict_index.values():
        if len(indices) < 2:
            continue
        for i, j in combinations(indices, 2):
            candidates[(i, j)] = _prefer(
                candidates.get((i, j)),
                "Mesmo nome após normalização",
                "forte",
            )

    # 2) Nome de um cadastro usado como alias em outro.
    for j in range(n):
        for alias in aliases[j]:
            for i in strict_index.get(alias, []):
                if i == j:
                    continue
                pair = _pair(i, j)
                candidates[pair] = _prefer(
                    candidates.get(pair),
                    "Nome de um cadastro aparece como alias do outro",
                    "forte",
                )

    # 3) Nome equivalente após retirar palavras de ligação.
    for indices in flex_index.values():
        if len(indices) < 2:
            continue
        for i, j in combinations(indices, 2):
            if strict_names[i] and strict_names[i] != strict_names[j]:
                pair = (i, j)
                candidates[pair] = _prefer(
                    candidates.get(pair),
                    "Nomes equivalentes após remover palavras de ligação",
                    "provável",
                )

    resultado: list[tuple[Any, ...]] = []
    for (i, j) in sorted(candidates):
        if not nomes[i] or not nomes[j]:
            continue
        chave = chave_duplicidade(nomes[i], nomes[j])
        if chave in accepted[i] and chave in accepted[j]:
            continue
        motivo, nivel = candidates[(i, j)]
        resultado.append((i, j, nomes[i], nomes[j], motivo, nivel))

    return tuple(resultado)


def possiveis_duplicidades(catalogo: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Retorna os mesmos sinais do fluxo histórico com índice e cache interno.

    O cache é invalidado automaticamente quando Nome, Aliases ou as decisões de
    saneamento relevantes mudam.
    """
    catalogo = list(catalogo or [])
    payload = _signature_payload(catalogo)
    rows = _possiveis_duplicidades_cached(payload)
    return [
        {
            "indices": (int(i), int(j)),
            "nomes": (str(nome_a), str(nome_b)),
            "motivo": str(motivo),
            "nivel": str(nivel),
        }
        for i, j, nome_a, nome_b, motivo, nivel in rows
    ]


def cache_info() -> dict[str, int]:
    info = _possiveis_duplicidades_cached.cache_info()
    return {
        "hits": info.hits,
        "misses": info.misses,
        "maxsize": info.maxsize or 0,
        "currsize": info.currsize,
    }
