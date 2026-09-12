"""Helpers leves da tela Histórico.

HF54: a pesquisa continua sendo feita sobre o conjunto completo; estes helpers
limitam apenas os registros renderizados pelo Streamlit em cada página.
"""
from __future__ import annotations

from typing import Sequence, TypeVar

T = TypeVar("T")


def total_paginas_historico(total: int, tamanho_pagina: int | None) -> int:
    total = max(0, int(total or 0))
    if tamanho_pagina is None:
        return 1
    tamanho = max(1, int(tamanho_pagina))
    return max(1, (total + tamanho - 1) // tamanho)


def paginar_historico(
    itens: Sequence[T], tamanho_pagina: int | None, pagina: int = 1
) -> tuple[list[T], int, int]:
    """Retorna itens visíveis + intervalo [inicio, fim) sem alterar a ordem."""
    total = len(itens)
    if tamanho_pagina is None:
        return list(itens), 0, total
    tamanho = max(1, int(tamanho_pagina))
    paginas = total_paginas_historico(total, tamanho)
    pagina = min(max(1, int(pagina or 1)), paginas)
    inicio = (pagina - 1) * tamanho
    fim = min(total, inicio + tamanho)
    return list(itens[inicio:fim]), inicio, fim
