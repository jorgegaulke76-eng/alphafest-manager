"""HF71 - resumo diario de prioridades comerciais, apenas leitura.

Usa contagens de filas existentes; nao deduz vendas, mensagens ou prazos novos.
"""
from __future__ import annotations
from datetime import date
from typing import Any


def resumo_diario_hf71(
    quadro: dict[str, Any] | None,
    sem_envio: list[dict[str, Any]] | None,
    retornos: list[dict[str, Any]] | None,
    hoje: date,
) -> dict[str, Any]:
    """Consolida sinais ja identificados; retorno elegivel e definido pela HF70."""
    quadro = quadro if isinstance(quadro, dict) else {}
    cadastro = quadro.get("cadastro") or []
    comercial = quadro.get("comercial") or []
    vistos_sem_envio = set()
    for proposta in sem_envio or []:
        if not isinstance(proposta, dict):
            continue
        numero = str(proposta.get("numero_proposta") or "").strip()
        if numero:
            vistos_sem_envio.add(numero)
    contagens = {"urgente": 0, "alta": 0, "normal": 0}
    for item in comercial:
        if not isinstance(item, dict):
            continue
        nivel = str(item.get("Prioridade") or "").casefold()
        if nivel in contagens:
            contagens[nivel] += 1
    aguardar = len({
        str(item.get("numero_proposta") or "").strip()
        for item in retornos or []
        if isinstance(item, dict)
        and str(item.get("numero_proposta") or "").strip()
        and str(item.get("nivel") or "").casefold() == "aguardar"
    })
    retorno_total = sum(contagens.values())
    cadastro_total = int(quadro.get("cadastro_total") or 0)
    # Apenas contagens no texto exportado: nao incluir dados pessoais/valores.
    linhas = [
        "ALPHAFEST | RESUMO DIARIO COMERCIAL",
        "Data de referencia: " + hoje.strftime("%d/%m/%Y"),
        "",
        "CONFERENCIAS CADASTRAIS: " + str(cadastro_total),
        "PROPOSTAS SEM REGISTRO DE ENVIO: " + str(len(vistos_sem_envio)),
        "RETORNOS ELEGIVEIS PARA CONFERIR: " + str(retorno_total),
        "  Urgentes: " + str(contagens["urgente"]),
        "  Altos: " + str(contagens["alta"]),
        "  Normais: " + str(contagens["normal"]),
        "RETORNOS MARCADOS AGUARDAR: " + str(aguardar),
        "",
        "Prioridade sugerida: conferir primeiro cadastros inconsistentes;",
        "validar registro de envio e depois revisar retornos comerciais.",
        "Estas contagens nao comprovam falta de resposta, venda ou pagamento.",
        "Nenhum envio, registro ou alteracao foi realizado.",
    ]
    return {
        "data": hoje.strftime("%d/%m/%Y"),
        "conferencias": cadastro_total,
        "sem_registro_envio": len(vistos_sem_envio),
        "retornos_elegiveis": retorno_total,
        "urgentes": contagens["urgente"],
        "altos": contagens["alta"],
        "normais": contagens["normal"],
        "aguardar": aguardar,
        "texto": "\n".join(linhas) + "\n",
    }
