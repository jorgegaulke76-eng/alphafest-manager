"""Leitura pura da Central do Site AlphaFest (HF35).

O módulo não mantém um cadastro paralelo do site. Ele interpreta o Catálogo
oficial do Manager e devolve indicadores de prontidão para a vitrine pública.
Persistência, permissões e navegação continuam sob responsabilidade do app.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List


def _texto(produto: Dict[str, Any], *chaves: str) -> str:
    for chave in chaves:
        valor = produto.get(chave)
        if valor is not None and str(valor).strip():
            return str(valor).strip()
    return ""


def _imagens(produto: Dict[str, Any]) -> List[str]:
    bruto = produto.get("Imagens", []) or []
    if isinstance(bruto, (str, bytes, bytearray)):
        bruto = [bruto]
    try:
        itens = list(bruto)
    except TypeError:
        itens = [bruto]
    saida: List[str] = []
    vistos = set()
    for item in itens:
        texto = str(item or "").strip()
        if texto and texto not in vistos:
            vistos.add(texto)
            saida.append(texto)
    return saida


def avaliar_produto_site(produto: Dict[str, Any]) -> Dict[str, Any]:
    """Avalia prontidão sem alterar nem completar dados do produto.

    Nome, descrição e foto são requisitos de apresentação. Preço e categoria
    geram aviso, mas não bloqueiam a vitrine porque muitos personalizados são
    orçados conforme quantidade/arte.
    """
    produto = produto or {}
    nome = _texto(produto, "Nome", "nome")
    descricao = _texto(produto, "DescricaoCompleta", "DescricaoCurta", "Descricao", "descricao")
    categoria = _texto(produto, "Categoria", "categoria")
    preco = _texto(produto, "Preco", "preco")
    imagens = _imagens(produto)
    ativo = produto.get("Ativo") is not False
    publicar = bool(produto.get("PublicarSite"))
    destaque = bool(produto.get("Destaque"))

    faltas: List[str] = []
    if not nome:
        faltas.append("Nome")
    if not descricao:
        faltas.append("Descrição")
    if not imagens:
        faltas.append("Foto")

    avisos: List[str] = []
    if not categoria:
        avisos.append("Categoria")
    if not preco:
        avisos.append("Valor sob consulta")

    pronto = bool(ativo and not faltas)
    return {
        "nome": nome or "Produto sem nome",
        "descricao": descricao,
        "categoria": categoria,
        "preco": preco,
        "imagens": imagens,
        "imagem_principal": imagens[0] if imagens else "",
        "ativo": ativo,
        "publicar_site": publicar,
        "destaque": destaque,
        "faltas": faltas,
        "avisos": avisos,
        "pronto": pronto,
        "status": "Pronto para vitrine" if pronto else "Revisar cadastro",
    }


def resumir_catalogo_site(catalogo: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    itens = [avaliar_produto_site(p) for p in (catalogo or []) if isinstance(p, dict)]
    ativos = [x for x in itens if x["ativo"]]
    marcados = [x for x in ativos if x["publicar_site"]]
    return {
        "total": len(itens),
        "ativos": len(ativos),
        "marcados_site": len(marcados),
        "destaques": sum(1 for x in marcados if x["destaque"]),
        "prontos_marcados": sum(1 for x in marcados if x["pronto"]),
        "revisar_marcados": sum(1 for x in marcados if not x["pronto"]),
        "prontos_nao_marcados": sum(1 for x in ativos if x["pronto"] and not x["publicar_site"]),
        "sem_foto_marcados": sum(1 for x in marcados if "Foto" in x["faltas"]),
        "sem_descricao_marcados": sum(1 for x in marcados if "Descrição" in x["faltas"]),
        "itens": itens,
    }


def ordenar_produtos_site(catalogo: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Retorna índices originais + leitura de prontidão em ordem de trabalho."""
    saida = []
    for indice, produto in enumerate(catalogo or []):
        if not isinstance(produto, dict):
            continue
        leitura = avaliar_produto_site(produto)
        leitura["indice_catalogo"] = indice
        leitura["produto"] = produto
        saida.append(leitura)
    saida.sort(
        key=lambda x: (
            not x["publicar_site"],
            not x["destaque"],
            not x["pronto"],
            x["nome"].casefold(),
        )
    )
    return saida
