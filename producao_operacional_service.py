"""20.4.9-I8.13.5-HF5 — regras puras de Produção e conclusão operacional.

Este módulo concentra decisões de mudança de etapa sem conhecer Streamlit,
Supabase ou session_state. O ``app.py`` continua responsável por persistência,
consumo de estoque, auditoria e mensagens.

Regras preservadas:
- Histórico/Proposta é a fonte oficial de Aprovado/Pronto/Entregue.
- ``producao_db`` guarda somente a etapa manual do trabalho.
- Entrar em produção (ou pular para Pronto/Entregue) exige a validação/consumo
  de materiais pelo orquestrador.
- Somente quando todos os itens ficam Pronto/Entregue o pedido pode receber
  ``Pronto = SIM``; todos Entregues permitem ``Entregue = SIM``.
- Reabrir uma etapa produtiva remove ``Pronto`` oficial, nunca ``Entregue``.
"""
from __future__ import annotations

import copy
from typing import Any, Iterable

from fluxo_operacional_service import normalizar_status_fluxo

ETAPAS_COM_CONSUMO = {"Em produção", "Pronto", "Entregue"}
ETAPAS_FINALIZADAS = {"Pronto", "Entregue"}


def etapa_exige_consumo(status_novo: Any) -> bool:
    """Indica se a etapa representa início/continuidade real de fabricação."""
    return normalizar_status_fluxo(status_novo) in ETAPAS_COM_CONSUMO


def validar_transicao_fluxo(
    *,
    proposta_encontrada: bool,
    proposta_encerrada: bool,
    aprovado: bool,
    entregue: bool,
    status_novo: Any,
) -> tuple[bool, str]:
    """Valida uma edição manual do Fluxo contra os status oficiais."""
    status = normalizar_status_fluxo(status_novo)
    if not proposta_encontrada:
        return False, "A proposta oficial não foi encontrada. Atualize os dados antes de alterar o Fluxo."
    if proposta_encerrada:
        return False, "Esta proposta está encerrada no Histórico e não pode avançar no Fluxo."
    if not bool(aprovado) and status != "Pedido recebido":
        return False, "Pedido ainda não aprovado no Histórico. Aprove a proposta antes de liberar arte/produção."
    if bool(entregue) and status != "Entregue":
        return False, "Pedido já está Entregue no Histórico. Reabra o status oficial antes de alterar a produção."
    return True, ""


def planejar_status_oficial_pos_fluxo(
    estados_tarefas: Iterable[Any],
    *,
    pronto_oficial: bool,
    entregue_oficial: bool,
) -> dict[str, Any] | None:
    """Decide a única alteração oficial decorrente do conjunto de etapas.

    Não altera a proposta. O chamador persiste via Fonte Única de Status.
    """
    estados = [normalizar_status_fluxo(s) for s in (estados_tarefas or [])]
    if not estados:
        return None
    if all(s == "Entregue" for s in estados):
        if not bool(entregue_oficial):
            return {"campo": "entregue", "valor": True, "motivo": "Todos os itens do Fluxo estão Entregues"}
        return None
    if all(s in ETAPAS_FINALIZADAS for s in estados):
        if not bool(pronto_oficial):
            return {"campo": "pronto", "valor": True, "motivo": "Todos os itens do Fluxo estão Prontos/Entregues"}
        return None
    if bool(pronto_oficial) and not bool(entregue_oficial):
        return {"campo": "pronto", "valor": False, "motivo": "Produção reaberta no Fluxo"}
    return None


def _adicionar_evento(tarefa: dict[str, Any], descricao: str, now_text: str) -> None:
    timeline = tarefa.get("timeline") if isinstance(tarefa.get("timeline"), list) else []
    timeline.append({"data": now_text, "descricao": descricao})
    tarefa["timeline"] = timeline[-50:]


def planejar_atalho_central(
    tarefas_base: Iterable[dict[str, Any]] | None,
    *,
    numero_proposta: str,
    acao: str,
    pode_iniciar_producao: bool,
    pode_marcar_pronto: bool,
    now_text: str,
    usuario_nome: str,
) -> dict[str, Any]:
    """Planeja atalhos da Central de Produção sem persistir nada.

    Retorna uma cópia das tarefas e a lista exata de mudanças a auditar.
    """
    numero = str(numero_proposta or "").strip()
    acao_norm = str(acao or "").strip().casefold()
    if not numero:
        return {"ok": False, "mensagem": "Pedido inválido.", "tarefas": [], "mudancas": []}
    if acao_norm not in {"iniciar", "pronto"}:
        return {"ok": False, "mensagem": "Ação de produção inválida.", "tarefas": [], "mudancas": []}
    if acao_norm == "iniciar" and not bool(pode_iniciar_producao):
        return {
            "ok": False,
            "mensagem": "O pedido ainda não está apto para iniciar produção. Revise materiais e etapa do Fluxo.",
            "tarefas": [], "mudancas": [],
        }
    if acao_norm == "pronto" and not bool(pode_marcar_pronto):
        return {
            "ok": False,
            "mensagem": "Para marcar o pedido como pronto, todos os itens precisam estar em produção ou já prontos.",
            "tarefas": [], "mudancas": [],
        }

    tarefas = copy.deepcopy(list(tarefas_base or []))
    mudancas: list[dict[str, str]] = []
    for tarefa in tarefas:
        if not isinstance(tarefa, dict) or not tarefa.get("ativa", True):
            continue
        if str(tarefa.get("numero_proposta") or "").strip() != numero:
            continue
        status_atual = normalizar_status_fluxo(tarefa.get("status"))
        novo_status = None
        if acao_norm == "iniciar" and status_atual == "Pronto para produzir":
            novo_status = "Em produção"
        elif acao_norm == "pronto" and status_atual == "Em produção":
            novo_status = "Pronto"
        if not novo_status or novo_status == status_atual:
            continue
        tarefa["status"] = novo_status
        tarefa["atualizado_em"] = str(now_text or "")
        _adicionar_evento(
            tarefa,
            f"Central de Produção: {status_atual} → {novo_status} por {str(usuario_nome or 'Sistema') or 'Sistema'}",
            str(now_text or ""),
        )
        mudancas.append({
            "tarefa_id": str(tarefa.get("id") or ""),
            "produto": str(tarefa.get("produto") or "Item do pedido"),
            "antes": status_atual,
            "depois": novo_status,
        })

    if not mudancas:
        return {"ok": False, "mensagem": "Nenhum item precisava desta atualização.", "tarefas": tarefas, "mudancas": []}
    return {
        "ok": True,
        "mensagem": "",
        "tarefas": tarefas,
        "mudancas": mudancas,
        "acao": acao_norm,
        "exige_consumo": acao_norm == "iniciar",
    }
