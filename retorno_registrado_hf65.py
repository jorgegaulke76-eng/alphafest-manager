"""HF65 - acompanhamento comercial manual com registro oficial do ultimo envio.

Sem banco, Streamlit ou envio de mensagens nesta camada. O link WhatsApp apenas
abre uma conversa depois de um clique do operador; envio continua manual.
"""
from __future__ import annotations

import re
from urllib.parse import quote

from proposal_status import resumo_status, valor_bool
from thu_comercial_service import aplicar_registro_envio


STATUS_OPERACIONAIS = frozenset({
    "pedido aprovado", "em produção", "em producao",
    "pronto", "entregue", "concluído", "concluido",
})


def link_whatsapp_retorno(numero: str, mensagem: str) -> str:
    """Preenche conversa somente para WhatsApp BR valido. Nao envia a mensagem."""
    digitos = re.sub(r"\D", "", str(numero or ""))
    if digitos.startswith("55") and len(digitos) in (12, 13):
        formato = digitos
    elif len(digitos) in (10, 11):
        formato = "55" + digitos
    else:
        return ""
    texto = str(mensagem or "").strip()
    if not texto or len(texto) > 1300:
        return ""
    return "https://wa.me/" + formato + "?text=" + quote(texto, safe="")


def validar_retorno_realizado(proposta, *, instante: str = "") -> tuple[bool, str]:
    """Valida novamente o status atual antes de registrar contato de verdade."""
    if not isinstance(proposta, dict):
        return False, "Proposta inválida."
    if not str(proposta.get("numero_proposta") or "").strip():
        return False, "Proposta sem número oficial."
    if not valor_bool(proposta.get("enviado")):
        return False, "Este orçamento ainda não tem envio inicial confirmado."
    estado = resumo_status(proposta)
    if any(estado.get(chave) for chave in (
        "aprovado", "pago", "pronto", "entregue", "encerrada", "concluida",
    )):
        return False, "A proposta está aprovada, encerrada ou em operação."
    if str(proposta.get("status") or "").strip().casefold() in STATUS_OPERACIONAIS:
        return False, "O status indica um pedido em operação."
    instante = str(instante or "").strip()
    ultimo = str(proposta.get("ultimo_envio_em") or "").strip()
    if instante and ultimo == instante:
        return False, "Já existe um retorno registrado neste minuto. Atualize a tela."
    return True, ""


def aplicar_retorno_realizado(proposta: dict, *, instante: str, usuario: str):
    """Atualiza apenas marcadores de envio do serviço oficial THU, in place."""
    instante = str(instante or "").strip()
    if not instante:
        raise ValueError("Data e hora do contato não informadas.")
    ok, motivo = validar_retorno_realizado(proposta, instante=instante)
    if not ok:
        raise ValueError(motivo)
    aplicar_registro_envio(proposta, now_text=instante, usuario=usuario)
    return proposta
