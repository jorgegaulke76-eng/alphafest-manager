"""20.4.9-I8.13.5-HF3 — regras puras de transição dos status oficiais.

A UI e a persistência ficam fora deste módulo. Aqui vivem apenas as regras
Aprovado -> Pago -> Pronto -> Entregue, carimbos e eventos decorrentes.
"""
from __future__ import annotations

from typing import Any, Callable

from proposal_status import resumo_status, proposta_concluida, proposta_faturamento_mensal, valor_bool

STATUS_FIELDS = ("aprovado", "pago", "pronto", "entregue")
STATUS_DATE_FIELDS = {
    "aprovado": "aprovado_em",
    "pago": "pago_em",
    "pronto": "pronto_em",
    "entregue": "entregue_em",
}
STATUS_LABELS = {
    "aprovado": "Orçamento aprovado",
    "pago": "Pagamento confirmado",
    "pronto": "Pedido pronto",
    "entregue": "Entrega concluída",
}


def normalizar_status_desejados(aprovado: Any, pago: Any, pronto: Any, entregue: Any) -> dict[str, bool]:
    entregue_b = valor_bool(entregue)
    return {
        "aprovado": valor_bool(aprovado),
        "pago": valor_bool(pago),
        "pronto": valor_bool(pronto) or entregue_b,
        "entregue": entregue_b,
    }


def snapshot_status(proposta: dict[str, Any] | None) -> dict[str, bool]:
    estado = resumo_status(proposta or {})
    return {campo: bool(estado.get(campo)) for campo in STATUS_FIELDS}


def status_persistidos_correspondem(proposta: dict[str, Any] | None, desejados: dict[str, bool]) -> bool:
    if not isinstance(proposta, dict):
        return False
    atual = snapshot_status(proposta)
    return all(atual[campo] == bool(desejados.get(campo)) for campo in STATUS_FIELDS)


def exige_consumo_material(estado_antes: dict[str, bool] | None, desejados: dict[str, bool]) -> bool:
    estado_antes = estado_antes or {}
    return bool(desejados.get("pronto") or desejados.get("entregue")) and not bool(estado_antes.get("pronto"))


def aplicar_status_na_proposta(
    proposta: dict[str, Any],
    desejados: dict[str, bool],
    *,
    now_text: str,
    usuario: str,
    registrar_evento: Callable[[dict[str, Any], str, str], Any] | None = None,
) -> dict[str, Any]:
    """Aplica transição no dicionário e devolve o contexto da mudança.

    Não grava banco e não registra auditoria externa. O callback de timeline é
    injetado pelo aplicativo para preservar o formato histórico já homologado.
    """
    anteriores = snapshot_status(proposta)
    antes_concluida = proposta_concluida(proposta)

    for campo in STATUS_FIELDS:
        proposta[campo] = bool(desejados.get(campo))

    mudancas: list[str] = []
    for campo in STATUS_FIELDS:
        valor_novo = bool(desejados.get(campo))
        valor_anterior = bool(anteriores.get(campo))
        campo_data = STATUS_DATE_FIELDS[campo]

        if valor_novo and not valor_anterior:
            if campo == "pronto":
                proposta["pronto_em"] = now_text
                proposta["pronto_por"] = usuario
                proposta["pronto_em_confiavel"] = True
            elif not proposta.get(campo_data):
                proposta[campo_data] = now_text
        elif not valor_novo and valor_anterior:
            proposta.pop(campo_data, None)
            if campo == "pronto":
                proposta.pop("pronto_por", None)
                proposta.pop("pronto_em_confiavel", None)

        if valor_anterior != valor_novo:
            texto = STATUS_LABELS[campo] if valor_novo else f"{STATUS_LABELS[campo]} desmarcado"
            mudancas.append(texto)
            if callable(registrar_evento):
                registrar_evento(proposta, texto, usuario)

    aprovou_agora = bool(desejados.get("aprovado")) and not bool(anteriores.get("aprovado"))
    depois_concluida = proposta_concluida(proposta)
    nova_conclusao = depois_concluida and not antes_concluida
    if nova_conclusao and callable(registrar_evento):
        descricao = "Entregue — operação finalizada e disponível no Histórico"
        if proposta_faturamento_mensal(proposta):
            descricao += "; pagamento segue para Faturamento Mensal"
        registrar_evento(proposta, descricao, usuario)

    return {
        "anteriores": anteriores,
        "mudancas": mudancas,
        "aprovou_agora": aprovou_agora,
        "nova_conclusao": nova_conclusao,
    }
