"""HF73: consulta local de categorias do roteiro, sem editar registros."""
from __future__ import annotations
from typing import Any

CATEGORIAS = (
    ("cadastro", "Conferências cadastrais"),
    ("envio", "Conferir registro de envio"),
    ("urgente", "Retornos urgentes"),
    ("alta", "Retornos de prioridade alta"),
    ("normal", "Retornos normais"),
)


def consultar_categoria_hf73(
    categoria: str,
    quadro: dict[str, Any] | None,
    sem_envio: list[dict[str, Any]] | None,
    *,
    busca: str = "",
    limite: int = 30,
) -> dict[str, Any]:
    """Retorna apenas numero, categoria e orientacao, jamais nomes ou telefone.

    A elegibilidade comercial vem exclusivamente do quadro HF70; sem envio
    nao e prova de mensagem nao enviada, e diagnostico nao e oportunidade.
    """
    quadro = quadro if isinstance(quadro, dict) else {}
    if categoria not in dict(CATEGORIAS):
        return {"total": 0, "registros": [], "exibidos": 0}
    fonte: list[dict[str, Any]] = []
    if categoria == "cadastro":
        for p in quadro.get("cadastro") or []:
            if isinstance(p, dict):
                fonte.append({
                    "Proposta": str(p.get("Proposta") or "").strip(),
                    "Situacao": str(p.get("Situacao") or "Conferir no Histórico"),
                    "Conferencia": "Revisar cadastro e vínculo manualmente",
                })
    elif categoria == "envio":
        for p in sem_envio or []:
            if isinstance(p, dict):
                fonte.append({
                    "Proposta": str(p.get("numero_proposta") or "").strip(),
                    "Situacao": "Sem registro de envio",
                    "Conferencia": "Verificar conversa real antes de registrar envio",
                })
    else:
        for p in quadro.get("comercial") or []:
            if isinstance(p, dict) and str(p.get("Prioridade") or "").casefold() == categoria:
                fonte.append({
                    "Proposta": str(p.get("Proposta") or "").strip(),
                    "Situacao": "Retorno " + categoria,
                    "Conferencia": "Revisar conversa e decidir contato manualmente",
                })
    pesquisa = str(busca or "").strip().casefold()
    vistos = set()
    registros = []
    for p in fonte:
        numero = p["Proposta"]
        if not numero or (pesquisa and pesquisa not in numero.casefold()):
            continue
        chave = (numero, p["Situacao"]) if categoria == "cadastro" else numero
        if chave in vistos:
            continue
        vistos.add(chave)
        registros.append(p)
    limite = max(1, min(int(limite), 100))
    return {"total": len(registros), "exibidos": min(len(registros), limite),
            "registros": registros[:limite]}
