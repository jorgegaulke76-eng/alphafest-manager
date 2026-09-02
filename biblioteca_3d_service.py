"""Serviço puro da Catálogo 3D interno do Jorge (HF23).

A interface e a persistência ficam em ``app.py``/``cloud_db.py``. Este módulo
concentra validações e transformação dos registros para manter o comportamento
testável sem Streamlit.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable
import re
import uuid

EXTENSOES_3D_PERMITIDAS = {
    ".3mf", ".stl", ".obj", ".step", ".stp", ".amf", ".zip", ".rar", ".7z",
    ".gcode", ".bgcode"
}
EXTENSOES_IMAGEM_PERMITIDAS = {".png", ".jpg", ".jpeg", ".webp"}


def extensao_arquivo(nome: str) -> str:
    return Path(str(nome or "").strip()).suffix.lower()


def arquivo_3d_valido(nome: str) -> bool:
    return extensao_arquivo(nome) in EXTENSOES_3D_PERMITIDAS


def imagem_valida(nome: str) -> bool:
    return extensao_arquivo(nome) in EXTENSOES_IMAGEM_PERMITIDAS


def sanitizar_texto(valor: object, limite: int = 4000) -> str:
    texto = re.sub(r"\s+", " ", str(valor or "").strip())
    return texto[: max(0, int(limite))]


def criar_registro(
    *,
    nome: str,
    descricao: str,
    tempo_impressao: str,
    imagem_path: str,
    arquivo_path: str,
    arquivo_nome: str,
    arquivo_tamanho: int = 0,
    criado_em: str | None = None,
    registro_id: str | None = None,
) -> dict:
    nome_limpo = sanitizar_texto(nome, 180)
    if not nome_limpo:
        raise ValueError("Informe o nome do modelo 3D.")
    if not str(imagem_path or "").strip():
        raise ValueError("Envie uma imagem do modelo.")
    if not str(arquivo_path or "").strip():
        raise ValueError("Envie o arquivo 3D.")
    if not arquivo_3d_valido(arquivo_nome):
        raise ValueError("Formato de arquivo 3D não suportado.")

    momento = str(criado_em or datetime.now().isoformat(timespec="seconds"))
    return {
        "id": str(registro_id or uuid.uuid4().hex),
        "nome": nome_limpo,
        "descricao": sanitizar_texto(descricao, 2500),
        "tempo_impressao": sanitizar_texto(tempo_impressao, 120),
        "imagem_path": str(imagem_path).strip(),
        "arquivo_path": str(arquivo_path).strip(),
        "arquivo_nome": Path(str(arquivo_nome)).name,
        "arquivo_tamanho": max(0, int(arquivo_tamanho or 0)),
        "criado_em": momento,
        "atualizado_em": momento,
    }


def ordenar_modelos(modelos: Iterable[dict]) -> list[dict]:
    itens = [dict(x) for x in (modelos or []) if isinstance(x, dict)]
    return sorted(
        itens,
        key=lambda x: (str(x.get("nome") or "").casefold(), str(x.get("criado_em") or "")),
    )


def filtrar_modelos(modelos: Iterable[dict], termo: str = "") -> list[dict]:
    termo_limpo = sanitizar_texto(termo, 200).casefold()
    itens = ordenar_modelos(modelos)
    if not termo_limpo:
        return itens
    saida = []
    for item in itens:
        alvo = " ".join(
            str(item.get(chave) or "")
            for chave in ("nome", "descricao", "tempo_impressao", "arquivo_nome")
        ).casefold()
        if termo_limpo in alvo:
            saida.append(item)
    return saida



def selecionar_modelos(modelos: Iterable[dict], ids_selecionados: Iterable[str]) -> list[dict]:
    """Retorna somente os modelos escolhidos, preservando a ordem alfabética do acervo."""
    ids = {str(x or "").strip() for x in (ids_selecionados or []) if str(x or "").strip()}
    return [x for x in ordenar_modelos(modelos) if str(x.get("id") or "").strip() in ids]


def modelo_para_produto_catalogo(modelo: dict, imagem_data_uri: str = "") -> dict:
    """Projeta um registro privado em um item seguro para o Catálogo 3D.

    Deliberadamente não copia ``arquivo_path``, ``arquivo_nome`` nem tamanho do
    arquivo. O catálogo para cliente recebe somente os dados visuais/comerciais
    combinados com o Jorge: nome, descrição, tempo e uma imagem.
    """
    modelo = dict(modelo or {})
    tempo = sanitizar_texto(modelo.get("tempo_impressao"), 120)
    produto = {
        "Nome": sanitizar_texto(modelo.get("nome"), 180) or "Modelo 3D",
        "Categoria": "Modelos 3D",
        "Subcategoria": "Impressão 3D",
        "DescricaoCurta": sanitizar_texto(modelo.get("descricao"), 2500),
        "Descricao": sanitizar_texto(modelo.get("descricao"), 2500),
        "Material": f"Tempo de impressão: {tempo}" if tempo else "Tempo de impressão: consultar",
        "Imagens": [str(imagem_data_uri).strip()] if str(imagem_data_uri or "").strip() else [],
        "Ativo": True,
        "biblioteca_3d_id": str(modelo.get("id") or "").strip(),
    }
    return produto

def tamanho_legivel(valor: int) -> str:
    tamanho = max(0, int(valor or 0))
    if tamanho < 1024:
        return f"{tamanho} B"
    if tamanho < 1024 * 1024:
        return f"{tamanho / 1024:.1f} KB"
    if tamanho < 1024 * 1024 * 1024:
        return f"{tamanho / (1024 * 1024):.1f} MB"
    return f"{tamanho / (1024 * 1024 * 1024):.1f} GB"
