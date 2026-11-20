"""HF65.24.45 — mensagens de atendimento sob demanda, sem envio ou gravação automática.

Não acessa estoque, pagamento, agenda ou banco. A equipe confirma cada envio
no WhatsApp. Os modelos não revelam detalhes de itens nem dados sensíveis.
"""
from __future__ import annotations

import re
from urllib.parse import quote

MODELOS = {
    "Aprovação da arte": (
        "Olá, {cliente}! Aqui é da AlphaFest. 😊\n"
        "A arte do pedido {pedido} está disponível para sua conferência. "
        "Você pode nos confirmar se está tudo certo antes de seguirmos com a produção?"
    ),
    "Pedido pronto": (
        "Olá, {cliente}! Aqui é da AlphaFest. 💙\n"
        "Seu pedido {pedido} está pronto! Entre em contato para combinarmos a retirada ou entrega."
    ),
    "Combinar entrega": (
        "Olá, {cliente}! Aqui é da AlphaFest. 💙\n"
        "Vamos combinar a retirada ou entrega do pedido {pedido}? "
        "Por favor, confirme o melhor horário."
    ),
}


def mensagem_modelo(tipo: str, pedido: str, cliente: str) -> str:
    if tipo not in MODELOS:
        raise ValueError("Modelo de mensagem desconhecido")
    # Dados do pedido vêm do cadastro; evitar quebras e entradas excessivas na mensagem.
    nome = re.sub(r"\s+", " ", str(cliente or "")).strip()[:80] or "tudo bem"
    numero = re.sub(r"\s+", " ", str(pedido or "")).strip()[:45] or "em atendimento"
    return MODELOS[tipo].format(cliente=nome, pedido=numero)


def numero_whatsapp(numero: object) -> str:
    digits = re.sub(r"\D", "", str(numero or ""))
    if len(digits) in (10, 11):
        digits = "55" + digits
    if not (12 <= len(digits) <= 13 and digits.startswith("55")):
        return ""
    return digits


def url_whatsapp(numero: object, mensagem: str) -> str:
    n = numero_whatsapp(numero)
    if not n or not str(mensagem or "").strip():
        return ""
    return f"https://wa.me/{n}?text={quote(str(mensagem).strip())}"
