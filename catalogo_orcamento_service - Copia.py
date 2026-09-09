"""Regras puras de Catálogo Oficial usadas pelo fluxo de orçamento.

I8.13.5-HF13

Este módulo não conhece Streamlit, Supabase nem session_state. Ele centraliza
identidade de produto, aliases, resolução híbrida Catálogo/texto livre, o
snapshot comercial seguro e o resumo de mídias usado na confirmação visual do
produto dentro do orçamento.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

ORCAMENTO_PRODUTO_LIVRE = "✍️ Digitar produto que não está no catálogo"


def normalizar_identidade_produto(valor: Any) -> str:
    """Normalização estrita para nome oficial/alias, compatível com a HF7."""
    texto = unicodedata.normalize("NFKD", str(valor or "").strip())
    texto = "".join(c for c in texto if not unicodedata.combining(c)).casefold()
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return " ".join(texto.split())


def aliases_catalogo_atomicos(produto: Optional[Mapping[str, Any]]) -> List[str]:
    """Expande aliases atuais/legados apenas para leitura, sem alterar cadastro."""
    produto = produto or {}
    bruto = produto.get("Aliases", [])
    if isinstance(bruto, (str, int, float)):
        valores = [bruto]
    elif isinstance(bruto, dict):
        valores = [bruto.get("Nome") or bruto.get("nome") or bruto.get("Alias") or bruto.get("alias") or ""]
    else:
        try:
            valores = list(bruto or [])
        except TypeError:
            valores = [bruto]

    resultado: List[str] = []
    vistos = set()
    for valor in valores:
        if isinstance(valor, dict):
            valor = valor.get("Nome") or valor.get("nome") or valor.get("Alias") or valor.get("alias") or ""
        texto = str(valor or "").strip()
        if not texto:
            continue
        candidatos = [texto]
        if re.search(r"[\n\r;,|•]", texto):
            candidatos.extend(x.strip() for x in re.split(r"(?:[\r\n]+|[;,|•]+)", texto) if x.strip())
        for candidato in candidatos:
            chave = normalizar_identidade_produto(candidato)
            if chave and chave not in vistos:
                vistos.add(chave)
                resultado.append(candidato)
    return resultado


def mapa_identidade_produtos(catalogo: Optional[Sequence[Mapping[str, Any]]]) -> Dict[str, str]:
    """Nome/alias normalizado -> nome oficial; nome oficial tem prioridade."""
    catalogo = catalogo or []
    mapa: Dict[str, str] = {}

    for produto in catalogo:
        nome = str((produto or {}).get("Nome") or "").strip()
        chave = normalizar_identidade_produto(nome)
        if chave and nome:
            mapa[chave] = nome

    for produto in catalogo:
        oficial = str((produto or {}).get("Nome") or "").strip()
        if not oficial:
            continue
        for alias in aliases_catalogo_atomicos(produto):
            chave = normalizar_identidade_produto(alias)
            if chave and chave not in mapa:
                mapa[chave] = oficial
    return mapa


def opcoes_produto_orcamento(
    catalogo: Optional[Sequence[Mapping[str, Any]]],
    *,
    rotulo_livre: str = ORCAMENTO_PRODUTO_LIVRE,
) -> Tuple[List[str], Dict[str, str]]:
    """Monta opções pesquisáveis preservando exatamente a semântica CAT1-HF4."""
    catalogo = catalogo or []
    opcoes = [rotulo_livre]
    mapa_rotulo: Dict[str, str] = {}
    vistos = set()

    for produto in catalogo:
        if not isinstance(produto, dict) or produto.get("Ativo") is False:
            continue
        oficial = str(produto.get("Nome") or "").strip()
        if not oficial:
            continue
        chave_oficial = normalizar_identidade_produto(oficial)
        if chave_oficial and chave_oficial not in vistos:
            vistos.add(chave_oficial)
            opcoes.append(oficial)
            mapa_rotulo[oficial] = oficial

    for produto in catalogo:
        if not isinstance(produto, dict) or produto.get("Ativo") is False:
            continue
        oficial = str(produto.get("Nome") or "").strip()
        if not oficial:
            continue
        for alias in aliases_catalogo_atomicos(produto):
            alias = str(alias or "").strip()
            if not alias or normalizar_identidade_produto(alias) == normalizar_identidade_produto(oficial):
                continue
            rotulo = f"{alias}  →  {oficial}"
            chave_rotulo = normalizar_identidade_produto(rotulo)
            if chave_rotulo in vistos:
                continue
            vistos.add(chave_rotulo)
            opcoes.append(rotulo)
            mapa_rotulo[rotulo] = oficial

    return opcoes, mapa_rotulo


def produto_catalogo_por_nome(
    catalogo: Optional[Sequence[Mapping[str, Any]]],
    nome_oficial: Any,
) -> Optional[Mapping[str, Any]]:
    chave = normalizar_identidade_produto(nome_oficial)
    if not chave:
        return None
    return next(
        (
            x
            for x in (catalogo or [])
            if isinstance(x, dict) and normalizar_identidade_produto(x.get("Nome")) == chave
        ),
        None,
    )


def resolver_produto_orcamento(
    escolha_catalogo: Any,
    texto_livre: Any,
    catalogo: Optional[Sequence[Mapping[str, Any]]],
    *,
    rotulo_livre: str = ORCAMENTO_PRODUTO_LIVRE,
) -> Tuple[str, Dict[str, str]]:
    """Resolve Catálogo explícito -> alias/nome digitado -> produto livre."""
    catalogo = catalogo or []
    _, mapa_rotulo = opcoes_produto_orcamento(catalogo, rotulo_livre=rotulo_livre)
    escolha = str(escolha_catalogo or "").strip()
    digitado = str(texto_livre or "").strip()

    oficial = ""
    origem = "livre"
    digitado_original = digitado

    if escolha and escolha != rotulo_livre:
        oficial = str(mapa_rotulo.get(escolha) or escolha).strip()
        origem = "catalogo"
    elif digitado:
        mapa = mapa_identidade_produtos(catalogo)
        resolvido = str(mapa.get(normalizar_identidade_produto(digitado)) or "").strip()
        if resolvido:
            oficial = resolvido
            origem = (
                "catalogo_alias"
                if normalizar_identidade_produto(resolvido) != normalizar_identidade_produto(digitado)
                else "catalogo"
            )
        else:
            oficial = digitado
            origem = "livre"

    produto_obj = produto_catalogo_por_nome(catalogo, oficial) if oficial and origem != "livre" else None
    meta = {
        "origem": origem,
        "digitado": digitado_original,
        "catalogo_id": str((produto_obj or {}).get("CatalogoId") or (produto_obj or {}).get("id") or ""),
        "produto_oficial": oficial if origem != "livre" else "",
    }
    return oficial, meta


def produto_catalogo_da_meta(
    meta: Optional[Mapping[str, Any]],
    catalogo: Optional[Sequence[Mapping[str, Any]]],
) -> Optional[Mapping[str, Any]]:
    """Retorna o produto explicitamente vinculado, sem adivinhação aproximada."""
    meta = meta or {}
    if str(meta.get("origem") or "") == "livre":
        return None
    catalogo = catalogo or []
    catalogo_id = str(meta.get("catalogo_id") or "").strip()
    oficial = str(meta.get("produto_oficial") or "").strip()
    if catalogo_id:
        achou = next(
            (
                x
                for x in catalogo
                if isinstance(x, dict)
                and str(x.get("CatalogoId") or x.get("id") or "").strip() == catalogo_id
            ),
            None,
        )
        if achou is not None:
            return achou
    return produto_catalogo_por_nome(catalogo, oficial)


def resumo_dados_catalogo(produto: Optional[Mapping[str, Any]]) -> str:
    """Texto auxiliar de UI; não injeta personalização no orçamento."""
    produto = produto or {}
    partes: List[str] = []
    categoria = str(produto.get("Categoria") or "").strip()
    sub = str(produto.get("Subcategoria") or "").strip()
    material = str(produto.get("Material") or "").strip()
    variacoes = [str(x).strip() for x in (produto.get("Variacoes", []) or []) if str(x).strip()]
    if categoria:
        partes.append(categoria + (f" / {sub}" if sub else ""))
    if material:
        partes.append(f"Material: {material}")
    if variacoes:
        partes.append("Opções: " + " • ".join(variacoes[:5]))
    return " · ".join(partes)



def midias_preview_catalogo(
    produto: Optional[Mapping[str, Any]],
    *,
    limite: int = 5,
) -> Dict[str, Any]:
    """HF11: retorna galeria segura para confirmação visual no Orçamento.

    A primeira foto continua sendo a principal. O vídeo é complementar e conta
    dentro do limite visual, preservando a regra já homologada de até cinco
    mídias por produto. A função é somente leitura e não altera o Catálogo.
    """
    produto = produto or {}
    try:
        limite_int = max(1, int(limite))
    except (TypeError, ValueError):
        limite_int = 5

    imagens: List[str] = []
    vistos = set()
    bruto_imagens = produto.get("Imagens", []) or []
    if isinstance(bruto_imagens, (str, bytes, bytearray)):
        bruto_imagens = [bruto_imagens]
    try:
        iter_imagens = list(bruto_imagens)
    except TypeError:
        iter_imagens = [bruto_imagens]

    for origem in iter_imagens:
        texto = str(origem or "").strip()
        if not texto or texto in vistos:
            continue
        vistos.add(texto)
        imagens.append(texto)

    video = str(
        produto.get("VideoCatalogo")
        or produto.get("Video")
        or produto.get("VideoUrl")
        or ""
    ).strip()

    max_fotos = limite_int - (1 if video else 0)
    if max_fotos < 0:
        max_fotos = 0
    imagens_visiveis = imagens[:max_fotos]
    total_catalogado = len(imagens) + (1 if video else 0)

    return {
        "imagem_principal": imagens_visiveis[0] if imagens_visiveis else "",
        "imagens": imagens_visiveis,
        "video": video,
        "tem_video": bool(video),
        "total_visivel": len(imagens_visiveis) + (1 if video else 0),
        "total_catalogado": total_catalogado,
        "limite": limite_int,
    }

def snapshot_item_catalogo(
    meta: Optional[Mapping[str, Any]],
    produto_catalogo: Optional[Mapping[str, Any]],
) -> Dict[str, str]:
    """HF13: identidade interna mínima do Catálogo no item da proposta.

    A descrição, material, categoria e mídias usados na confirmação visual
    permanecem somente no Catálogo/UI e não são persistidos no item da proposta.
    Isso reforça a separação entre a prévia interna e o conteúdo público enviado
    ao cliente. Tema, nome, cor/material e detalhes do pedido seguem manuais.
    """
    meta = meta or {}
    _ = produto_catalogo  # assinatura preservada por compatibilidade
    return {
        "produto_origem": str(meta.get("origem") or "livre"),
        "produto_digitado": str(meta.get("digitado") or ""),
        "produto_catalogo_id": str(meta.get("catalogo_id") or ""),
    }
