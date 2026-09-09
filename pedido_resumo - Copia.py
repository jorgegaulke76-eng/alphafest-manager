"""Resumo operacional compacto dos produtos de uma proposta/pedido.

Fonte única visual: sempre lê os itens da própria proposta oficial. Não consulta
estoque, ficha técnica ou produção e não persiste nenhum dado.
"""
from __future__ import annotations

from typing import Any


def _qtd(valor: Any) -> str:
    try:
        numero = float(valor or 0)
    except (TypeError, ValueError):
        return str(valor or "0").strip() or "0"
    if abs(numero - round(numero)) < 1e-9:
        return str(int(round(numero)))
    return (f"{numero:.3f}").rstrip("0").rstrip(".").replace(".", ",")


def resumo_produtos_pedido(proposta: dict[str, Any] | None, limite: int = 2, max_chars: int = 120) -> str:
    """Retorna ex.: ``5× Caneca Porcelana · 30× Adesivo DTF · +2 itens``."""
    proposta = proposta or {}
    itens = [i for i in (proposta.get("itens") or []) if isinstance(i, dict)]
    partes: list[str] = []
    for item in itens:
        nome = str(item.get("produto") or item.get("nome") or "Produto").strip() or "Produto"
        quantidade = _qtd(item.get("quantidade", item.get("qtd", 0)))
        partes.append(f"{quantidade}× {nome}")
    if not partes:
        return "Sem itens informados"
    limite = max(1, int(limite or 1))
    exibidas = partes[:limite]
    restante = max(0, len(partes) - len(exibidas))
    texto = " · ".join(exibidas)
    if restante:
        texto += f" · +{restante} item" + ("s" if restante != 1 else "")
    max_chars = max(40, int(max_chars or 120))
    if len(texto) > max_chars:
        texto = texto[: max_chars - 1].rstrip(" ·,-") + "…"
    return texto
