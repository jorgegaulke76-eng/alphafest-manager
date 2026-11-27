"""HF64 - encerramento assistido de orcamentos sem retorno, sem exclusao.

Nucleo puro: nenhuma conexao com Streamlit, banco ou Telegram.
O tempo decorrido so permite exibir o botao; a ausencia de resposta deve ser
confirmada pelo operador apos conferir a conversa real.
"""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo
from typing import Any

from proposal_status import resumo_status, valor_bool

MIN_DIAS_PARA_ENCERRAR = 3
_FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")


def _data_ultimo_envio(valor: Any) -> date | None:
    if isinstance(valor, datetime):
        return valor.astimezone(_FUSO_BRASILIA).date() if valor.tzinfo else valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor or "").strip()
    if not texto:
        return None
    # O Manager registra datas locais no formato brasileiro.
    if len(texto) >= 10 and texto[2] == "/" and texto[5] == "/":
        try:
            return datetime.strptime(texto[:10], "%d/%m/%Y").date()
        except ValueError:
            return None
    try:
        dt = datetime.fromisoformat(texto.replace("Z", "+00:00"))
        return dt.astimezone(_FUSO_BRASILIA).date() if dt.tzinfo else dt.date()
    except ValueError:
        return None


def elegibilidade_encerramento(proposta: dict[str, Any] | None, hoje: date, minimo_dias: int = MIN_DIAS_PARA_ENCERRAR) -> tuple[bool, str]:
    """Bloqueia propostas sem envio comprovado, recentes, pagas ou operacionais."""
    if not isinstance(proposta, dict):
        return False, "Proposta inválida."
    if not str(proposta.get("numero_proposta") or "").strip():
        return False, "A proposta não possui número oficial."
    estado = resumo_status(proposta)
    if any(estado.get(campo) for campo in ("aprovado", "pago", "pronto", "entregue", "encerrada", "concluida")):
        return False, "Proposta aprovada, paga, concluída ou encerrada não pode ser fechada por este atalho."
    if str(proposta.get("status") or "").strip().casefold() in {
        "pedido aprovado", "em produção", "em producao", "pronto", "entregue", "concluído", "concluido",
    }:
        return False, "O status indica pedido em operação; confira o Histórico."
    if not valor_bool(proposta.get("enviado")):
        return False, "Sem registro de envio real. Confira a seção Orçamentos sem registro de envio."
    ultima_data = _data_ultimo_envio(proposta.get("ultimo_envio_em") or proposta.get("enviado_em"))
    if ultima_data is None:
        return False, "Data do envio não confiável: confira o Histórico antes de encerrar."
    if not isinstance(hoje, date):
        return False, "Data atual inválida."
    dias = (hoje - ultima_data).days
    if dias < 0:
        return False, "Data do último envio está no futuro."
    if dias < minimo_dias:
        return False, f"Aguarde pelo menos {minimo_dias} dias desde o último envio real."
    return True, ""


def aplicar_encerramento_sem_retorno(
    proposta: dict[str, Any],
    *,
    hoje: date,
    agora_texto: str,
    usuario: str,
) -> dict[str, Any]:
    """Altera somente marcadores comerciais; preserva itens, valores e vinculos."""
    permitido, motivo = elegibilidade_encerramento(proposta, hoje)
    if not permitido:
        raise ValueError(motivo)
    proposta["nao_fechado_sem_retorno"] = True
    proposta["nao_fechado_pagamento"] = False
    proposta["status_comercial"] = "nao_fechado_sem_retorno"
    proposta["encerrado"] = True
    proposta["encerrado_sem_retorno_em"] = str(agora_texto)
    proposta["encerrado_sem_retorno_por"] = str(usuario or "Jorge")
    return proposta
