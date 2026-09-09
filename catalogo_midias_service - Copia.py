"""Regras puras para manutenção da galeria de fotos do Catálogo AlphaFest."""

from __future__ import annotations

from typing import Iterable, Sequence


def _limpar_refs(valores: Iterable[object] | None) -> list[str]:
    vistos: set[str] = set()
    saida: list[str] = []
    for valor in valores or []:
        ref = str(valor or "").strip()
        if not ref or ref in vistos:
            continue
        vistos.add(ref)
        saida.append(ref)
    return saida


def resolver_galeria_fotos(
    imagens_cadastradas: Sequence[object] | None,
    remover_indices: Iterable[int] | None,
    principal_indice: int | None,
    urls_digitadas: Iterable[object] | None,
    novas_referencias: Iterable[object] | None = None,
    *,
    substituir_todas: bool = False,
) -> list[str]:
    """Monta a galeria final sem ressuscitar fotos removidas.

    Regras:
    - fotos marcadas para remoção não voltam por causa do campo de URLs;
    - apagar manualmente uma URL também a remove do cadastro;
    - a ordem atual é preservada sempre que possível;
    - a foto escolhida como principal só é recolocada na frente se ainda existir;
    - removendo a principal, a primeira foto restante/nova assume automaticamente;
    - ``substituir_todas`` ignora toda a galeria antiga.
    """
    atuais = _limpar_refs(imagens_cadastradas)
    removidos_idx = {
        int(i)
        for i in (remover_indices or [])
        if isinstance(i, int) or str(i).lstrip("-").isdigit()
    }
    removidos_idx = {i for i in removidos_idx if 0 <= i < len(atuais)}
    removidas = {atuais[i] for i in removidos_idx}

    urls = [u for u in _limpar_refs(urls_digitadas) if u not in removidas]
    urls_set = set(urls)

    finais: list[str] = []
    if not substituir_todas:
        for i, ref in enumerate(atuais):
            if i in removidos_idx:
                continue
            if ref.startswith(("http://", "https://")) and ref not in urls_set:
                # Campo de URLs também funciona como editor: linha apagada = URL removida.
                continue
            if ref not in finais:
                finais.append(ref)

        # URLs novas digitadas entram depois das referências já existentes.
        for ref in urls:
            if ref not in finais:
                finais.append(ref)
    else:
        finais.extend(urls)

    for ref in _limpar_refs(novas_referencias):
        if ref not in finais:
            finais.append(ref)

    principal_ref = ""
    try:
        idx_principal = int(principal_indice) if principal_indice is not None else -1
    except (TypeError, ValueError):
        idx_principal = -1
    if (
        not substituir_todas
        and 0 <= idx_principal < len(atuais)
        and idx_principal not in removidos_idx
    ):
        principal_ref = atuais[idx_principal]

    # Nunca reintroduz uma foto principal removida/apagada. Se ela não existe mais,
    # a primeira referência restante já passa a ser a nova principal.
    if principal_ref and principal_ref in finais:
        finais.remove(principal_ref)
        finais.insert(0, principal_ref)

    return finais


def chave_estado_catalogo_pertence_ao_formulario(chave: object, sufixo: object) -> bool:
    """Identifica todo widget cat_* do formulário, inclusive chaves com índice final."""
    chave_txt = str(chave or "")
    sufixo_txt = str(sufixo or "")
    if not chave_txt.startswith("cat_") or not sufixo_txt:
        return False
    token = f"_{sufixo_txt}"
    return chave_txt.endswith(token) or f"{token}_" in chave_txt
