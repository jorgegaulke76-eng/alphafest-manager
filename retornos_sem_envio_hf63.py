"""Selecao conservadora de orcamentos sem registro de envio (HF63).

Sem banco, sem envio de mensagens e sem alteracao de propostas.
A ausencia de registro NAO prova que o cliente nao recebeu o orcamento.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from proposal_status import resumo_status, valor_bool


def _data_proposta(proposta: dict[str, Any]) -> date:
    for campo in ("data_geracao", "criado_em", "data"):
        valor = str(proposta.get(campo) or "").strip()
        if not valor:
            continue
        for formato in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(valor[:10], formato).date()
            except ValueError:
                pass
    return date.min


def listar_sem_registro_envio(historico: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Lista propostas oficiais pendentes, mesmo as legadas sem atendimento_id.

    Duplicatas por numero sao mostradas uma vez, sem alterar o Historico.
    Exclui pedidos aprovados/pagos/em producao/concluidos/encerrados.
    """
    resultado = []
    ids = set()
    for proposta in historico or []:
        if not isinstance(proposta, dict):
            continue
        numero = str(proposta.get("numero_proposta") or "").strip()
        if not numero or numero in ids:
            continue
        ids.add(numero)
        estado = resumo_status(proposta)
        if any(estado.get(campo) for campo in ("aprovado", "pago", "pronto", "entregue", "encerrada", "concluida")):
            continue
        if valor_bool(proposta.get("enviado")):
            continue
        if str(proposta.get("status") or "").strip().casefold() in {
            "pedido aprovado", "em produção", "pronto", "entregue", "concluido", "concluído"
        }:
            continue
        resultado.append(proposta)
    resultado.sort(key=_data_proposta, reverse=True)
    return resultado
