"""HF70: quadro de prioridades conservador, baseado nas filas oficiais e sem escrita."""
from __future__ import annotations
from collections import Counter
from typing import Any

TIPOS_CRITICOS = frozenset((
    "Numero de proposta repetido", "Proposta sem numero",
    "ID de atendimento repetido", "Atendimento nao encontrado",
    "Sem atendimento vinculado",
))


def quadro_prioridades_hf70(pendencias: list[dict[str, Any]] | None,
                           retornos: list[dict[str, Any]] | None,
                           sem_envio: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Pendencia cadastral nao e lead. Retorno requer sinal independente na fila existente."""
    pendencias_validas = [p for p in (pendencias or [])
                         if isinstance(p, dict) and p.get("Situacao") in TIPOS_CRITICOS]
    bloqueados = {str(p.get("Proposta") or "").strip()
                  for p in pendencias_validas}
    totais = Counter(str(p.get("Situacao")) for p in pendencias_validas)
    documentos = []
    vistos = set()
    for p in pendencias_validas:
        numero = str(p.get("Proposta") or "Sem numero").strip()
        situacao = str(p["Situacao"])
        chave = (numero, situacao)
        if chave in vistos:
            continue
        vistos.add(chave)
        documentos.append({"Proposta": numero, "Situacao": situacao,
                           "Proxima acao": "Conferir manualmente o Histórico e a conversa original"})

    envios = set()
    for p in sem_envio or []:
        if not isinstance(p, dict):
            continue
        numero = str(p.get("numero_proposta") or "").strip()
        if numero:
            envios.add(numero)

    comerciais = []
    vistos_retornos = set()
    for r in retornos or []:
        if not isinstance(r, dict):
            continue
        numero = str(r.get("numero_proposta") or "").strip()
        nivel = str(r.get("nivel") or "").strip().casefold()
        if not numero or numero in vistos_retornos or numero in bloqueados or numero in envios:
            continue
        if nivel not in ("normal", "alta", "urgente"):
            continue
        vistos_retornos.add(numero)
        comerciais.append({
            "Proposta": numero, "Prioridade": nivel,
            "Proxima acao": "Conferir o retorno sugerido no painel de orçamentos enviados",
        })
    ordem = {"urgente": 0, "alta": 1, "normal": 2}
    comerciais.sort(key=lambda x: (ordem[x["Prioridade"]], x["Proposta"]))
    return {
        "cadastro": documentos,
        "comercial": comerciais,
        "cadastro_total": len(pendencias_validas),
        "comercial_total": len(comerciais),
        "tipos_cadastro": dict(totais),
        "retornos_bloqueados_por_conferencia": len({
            str(r.get("numero_proposta") or "").strip()
            for r in retornos or [] if isinstance(r, dict)
            and str(r.get("numero_proposta") or "").strip() in bloqueados
            and str(r.get("nivel") or "").strip().casefold() in ("normal", "alta", "urgente")
        }),
    }
