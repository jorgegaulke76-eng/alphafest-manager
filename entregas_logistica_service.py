"""20.4.9-I8.13.5-HF6 — regras puras de Entregas, Retiradas e Logística.

Este módulo não conhece Streamlit, Supabase ou session_state. A proposta oficial
continua sendo a fonte única de Pronto/Entregue; aqui vivem somente as regras de
metadados logísticos, mensagem ao cliente e validação da conclusão da saída.

Regras preservadas:
- logística descreve a saída e nunca cria status paralelo;
- formas válidas: Retirada na AlphaFest, Entrega AlphaFest, Motoboy e Outro;
- registrar aviso grava carimbo/usuário na própria proposta;
- somente pedido oficialmente Pronto e ainda não Entregue pode concluir saída;
- concluir saída planeja ``Entregue = SIM``; a persistência oficial continua no
  serviço/status do aplicativo, que mantém ``Entregue -> Pronto``.
"""
from __future__ import annotations

from typing import Any, Callable

from proposal_status import resumo_status

TIPOS_SAIDA_VALIDOS = (
    "Retirada na AlphaFest",
    "Entrega AlphaFest",
    "Motoboy",
    "Outro",
)


def normalizar_tipo_saida(valor: Any) -> str:
    tipo = str(valor or "").strip()
    if tipo and tipo not in TIPOS_SAIDA_VALIDOS:
        raise ValueError("Forma de saída inválida.")
    return tipo


def aplicar_logistica_na_proposta(
    proposta: dict[str, Any],
    *,
    tipo_entrega: Any = None,
    observacao: Any = None,
    marcar_avisado: bool = False,
    agora_texto: str = "",
    usuario: str = "Sistema",
    registrar_evento: Callable[[dict[str, Any], str, str], Any] | None = None,
) -> dict[str, Any]:
    """Aplica somente metadados logísticos e devolve o contexto da mudança.

    A função altera o dicionário recebido, como o updater histórico já fazia,
    porém não persiste nem registra auditoria externa.
    """
    if not isinstance(proposta, dict):
        raise TypeError("Proposta inválida.")

    antes = {
        "logistica_tipo": proposta.get("logistica_tipo"),
        "logistica_observacao": proposta.get("logistica_observacao"),
        "cliente_avisado_em": proposta.get("cliente_avisado_em"),
        "cliente_avisado_por": proposta.get("cliente_avisado_por"),
    }
    mudou = False

    if tipo_entrega is not None:
        tipo = normalizar_tipo_saida(tipo_entrega)
        if str(proposta.get("logistica_tipo") or "") != tipo:
            proposta["logistica_tipo"] = tipo
            mudou = True

    if observacao is not None:
        obs = str(observacao or "").strip()[:500]
        if str(proposta.get("logistica_observacao") or "") != obs:
            proposta["logistica_observacao"] = obs
            mudou = True

    evento = ""
    if bool(marcar_avisado):
        proposta["cliente_avisado_em"] = str(agora_texto or "")
        proposta["cliente_avisado_por"] = str(usuario or "Sistema")
        mudou = True
        evento = "Cliente avisado: pedido pronto para retirada/entrega"
    elif mudou:
        evento = "Dados de entrega/retirada atualizados"

    if evento and callable(registrar_evento):
        registrar_evento(proposta, evento, str(usuario or "Sistema"))

    depois = {
        "logistica_tipo": proposta.get("logistica_tipo"),
        "logistica_observacao": proposta.get("logistica_observacao"),
        "cliente_avisado_em": proposta.get("cliente_avisado_em"),
        "cliente_avisado_por": proposta.get("cliente_avisado_por"),
    }
    return {
        "antes": antes,
        "depois": depois,
        "mudou": mudou,
        "evento": evento,
    }


def mensagem_pedido_pronto(proposta: dict[str, Any] | None) -> str:
    proposta = proposta or {}
    cliente = str(proposta.get("cliente_nome") or "").strip().title() or "cliente"
    numero = str(proposta.get("numero_proposta") or "pedido")
    tipo = str(proposta.get("logistica_tipo") or "").strip()
    complemento = {
        "Retirada na AlphaFest": "Seu pedido já está disponível para retirada na AlphaFest.",
        "Entrega AlphaFest": "Seu pedido está pronto e vamos organizar a entrega com você.",
        "Motoboy": "Seu pedido está pronto e podemos organizar o envio por motoboy.",
    }.get(tipo, "Seu pedido está pronto para retirada/entrega.")
    return f"Olá, {cliente}! 😊 {complemento} Pedido {numero}. Qualquer dúvida, estamos à disposição. — AlphaFest"


def validar_conclusao_saida(
    proposta: dict[str, Any] | None,
    *,
    confirmar_saida: bool,
) -> dict[str, Any]:
    """Valida a ação logística antes de pedir ``Entregue = SIM`` ao status oficial."""
    if not bool(confirmar_saida):
        return {"ok": False, "mensagem": "Confirme a saída antes de marcar o pedido como Entregue."}
    if not isinstance(proposta, dict):
        return {"ok": False, "mensagem": "A proposta oficial não foi encontrada. Atualize a tela e tente novamente."}

    status = resumo_status(proposta)
    if status.get("entregue"):
        return {"ok": False, "mensagem": "Este pedido já está Entregue no Histórico."}
    if not status.get("ativa"):
        return {"ok": False, "mensagem": "Este pedido está encerrado e não pode concluir saída pela Central de Entregas."}
    if not status.get("pronto"):
        return {"ok": False, "mensagem": "O pedido ainda não está oficialmente Pronto para retirada/entrega."}

    return {
        "ok": True,
        "mensagem": "",
        "campo_status": "entregue",
        "valor_status": True,
    }
