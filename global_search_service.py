"""Índice leve da Pesquisa Global do AlphaFest Manager.

HF24 — separa a montagem do índice da consulta digitada. O índice é montado
somente quando os documentos de origem mudam; cada tecla pesquisada consulta
strings já preparadas em memória em vez de reconstruir/deepcopiar todas as bases.
"""
from __future__ import annotations

from typing import Any, Callable


RESULT_KEYS = ("clientes", "propostas", "produtos", "atendimentos", "projetos", "componentes")


def _low(value: Any) -> str:
    return str(value or "").lower()


def build_global_search_index(
    *,
    clientes: list[dict[str, Any]],
    propostas: list[dict[str, Any]],
    produtos: list[dict[str, Any]],
    atendimentos: dict[str, Any],
    componentes: dict[str, list[Any]],
    projetos: list[dict[str, Any]],
    proposal_text: Callable[[dict[str, Any]], str],
    project_components_text: Callable[[dict[str, Any]], str],
) -> dict[str, list[tuple[str, Any]]]:
    """Pré-calcula os textos pesquisáveis mantendo ordem e sem alterar os dados."""
    index: dict[str, list[tuple[str, Any]]] = {key: [] for key in RESULT_KEYS}

    for cliente in clientes or []:
        base = " ".join(
            str(cliente.get(c, ""))
            for c in (
                "nome", "documento", "whatsapp", "email", "cidade", "observacoes",
                "segmentos", "interesses", "campanhas_interesse",
            )
        ).lower()
        index["clientes"].append((base, cliente))

    for proposta in propostas or []:
        index["propostas"].append((_low(proposal_text(proposta)), proposta))

    for indice, produto in enumerate(produtos or []):
        base = (
            " ".join(
                str(produto.get(c, ""))
                for c in (
                    "Nome", "Categoria", "Subcategoria", "CodigoInterno", "Descricao",
                    "DescricaoCurta", "DescricaoCompleta", "PalavrasChave", "Tags",
                )
            )
            + " "
            + " ".join(str(x) for x in (produto.get("Aliases", []) or []))
        ).lower()
        index["produtos"].append((base, (indice, produto)))

    itens_atendimento = atendimentos.get("itens", []) if isinstance(atendimentos, dict) else []
    for atendimento in itens_atendimento or []:
        base = " ".join(
            str(atendimento.get(c, ""))
            for c in ("cliente", "telefone", "mensagem", "status", "assunto", "responsavel")
        ).lower()
        index["atendimentos"].append((base, atendimento))

    for categoria, valores in (componentes or {}).items():
        for valor in valores or []:
            base = f"{categoria} {valor}".lower()
            index["componentes"].append((base, {"categoria": categoria, "valor": valor}))

    for projeto in projetos or []:
        arquivos = projeto.get("arquivos", []) if isinstance(projeto.get("arquivos"), list) else []
        partes = [
            projeto.get("cliente", ""), projeto.get("tema", ""), projeto.get("produto", ""),
            projeto.get("numero_proposta", ""), projeto.get("observacoes", ""),
            project_components_text(projeto), projeto.get("caracteristicas_livres", ""),
            projeto.get("necessidade", ""), projeto.get("detalhes", ""),
        ]
        for arquivo in arquivos:
            partes.extend([arquivo.get("nome", ""), arquivo.get("descricao", ""), arquivo.get("tags", "")])
        index["projetos"].append((" ".join(map(str, partes)).lower(), projeto))

    return index


def query_global_search_index(
    index: dict[str, list[tuple[str, Any]]],
    termo: str,
    *,
    limite_por_tipo: int = 8,
) -> dict[str, list[Any]]:
    """Consulta o índice preservando o mesmo limite e a ordem histórica da busca."""
    needle = str(termo or "").strip().lower()
    result = {key: [] for key in RESULT_KEYS}
    if len(needle) < 2:
        return result

    limit = max(1, int(limite_por_tipo or 1))
    for key in RESULT_KEYS:
        for haystack, payload in index.get(key, []):
            if needle not in haystack:
                continue
            if key == "produtos":
                indice, produto = payload
                registro = dict(produto)
                registro["_indice_catalogo"] = indice
                result[key].append(registro)
            else:
                result[key].append(payload)
            if len(result[key]) >= limit:
                break
    return result
