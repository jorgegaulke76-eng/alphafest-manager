"""Seletor de preços compatível com o catálogo oficial."""
from typing import Any, MutableMapping

MODALIDADES = {
    "sob_orcamento": "Sob orçamento — Consultar valores",
    "fixo": "Preço fixo",
    "a_partir": "Preço inicial — A partir de",
}

def modalidade_atual(produto: MutableMapping[str, Any]) -> str:
    modo = str(produto.get("ModalidadePrecoSite") or "").strip().lower()
    if modo in MODALIDADES:
        return modo
    return "fixo" if produto.get("ExibirPrecoSite") is True else "sob_orcamento"

def aplicar_modalidade(produto: MutableMapping[str, Any], modo: str) -> bool:
    if modo not in MODALIDADES:
        raise ValueError("Modalidade de preço inválida")
    antes = (produto.get("ModalidadePrecoSite"), produto.get("ExibirPrecoSite"))
    produto["ModalidadePrecoSite"] = modo
    produto["ExibirPrecoSite"] = modo != "sob_orcamento"
    return antes != (produto["ModalidadePrecoSite"], produto["ExibirPrecoSite"])

def seletor_modalidade_preco(st: Any, produto: MutableMapping[str, Any], *, key: str) -> bool:
    """Use dentro do formulário existente, com o autosave já implementado no Manager."""
    atual = modalidade_atual(produto)
    codigos = list(MODALIDADES)
    escolhido = st.selectbox(
        "Preço exibido no site", codigos, index=codigos.index(atual),
        format_func=lambda m: MODALIDADES[m], key=key,
        help="A partir de exige um produto básico realmente disponível no preço anunciado.",
    )
    return aplicar_modalidade(produto, escolhido) if escolhido != atual else False
