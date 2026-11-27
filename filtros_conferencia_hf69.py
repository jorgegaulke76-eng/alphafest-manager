"""HF69: busca e filtro da fila de vinculos, sem persistencia."""
from __future__ import annotations
from typing import Any


def filtrar_fila_vinculos(registros: list[dict[str, Any]] | None,
                         numero: str = "", situacao: str = "Todas") -> list[dict[str, Any]]:
    """Filtra apenas numero de proposta e situacao; nunca altera registros."""
    busca = str(numero or "").strip().casefold()
    filtro = str(situacao or "Todas").strip()
    return [
        dict(item) for item in (registros or [])
        if isinstance(item, dict)
        and (not busca or busca in str(item.get("Proposta") or "").casefold())
        and (filtro == "Todas" or item.get("Situacao") == filtro)
    ]
