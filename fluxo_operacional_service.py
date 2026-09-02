"""20.4.9-I8.13.5 — serviço puro do Fluxo Operacional.

Este módulo concentra regras de projeção Histórico -> Fluxo sem depender de
Streamlit, session_state ou acesso ao banco. A tela/orquestrador continua em
``app.py``; aqui ficam apenas regras determinísticas e testáveis.

Contrato:
- Histórico/Proposta é a fonte oficial de existência e status.
- ``producao_db`` preserva somente campos manuais da etapa operacional.
- Reconciliação nunca inventa status oficiais da proposta.
"""
from __future__ import annotations

import copy
from typing import Any, Iterable

from constants import STATUS_FLUXO
from proposal_status import proposta_ativa_operacional, resumo_status
from central_producao_engine import (
    reconciliar_etapa_status_oficial,
    reconciliar_etapa_aprovacao_oficial,
)

try:
    from tempo_ciclo_producao_service import aplicar_transicao_ciclo as _aplicar_transicao_ciclo
except Exception:
    def _aplicar_transicao_ciclo(tarefa, status_anterior, status_novo, *, now_text, usuario_nome="Sistema"):
        return copy.deepcopy(tarefa or {})


def inferir_processos(produto: Any, especificacoes: Any = "") -> list[str]:
    texto = f"{produto or ''} {especificacoes or ''}".lower()
    processos: list[str] = []
    if any(x in texto for x in ["personaliz", "tema:", "nome:", "topo", "convite", "caixa", "tag"]):
        processos.append("Criação/ajuste de arte")
    if "papel de arroz" in texto or "papel arroz" in texto:
        processos.append("Papel de arroz")
    if any(x in texto for x in ["3d", "pla", "impressão 3d", "impressao 3d"]):
        processos.append("Impressão 3D")
    if any(x in texto for x in ["laser", "mdf", "acrílico", "acrilico"]):
        processos.append("Corte/laser")
    if any(x in texto for x in ["balão", "balao", "bubble", "balloon", "arco"]):
        processos.append("Balões")
    if any(x in texto for x in ["papelaria", "topo", "caixa", "adesivo", "tag", "convite", "banner", "faixa"]):
        processos.append("Impressão papelaria")
    if any(x in texto for x in ["montagem", "cachepô", "cachepo", "lembranc", "tubolata", "centro de mesa"]):
        processos.append("Montagem")
    if not processos:
        processos = ["Montagem", "Acabamento"]
    return list(dict.fromkeys(processos))


def status_inicial_fluxo(produto: Any, especificacoes: Any = "") -> str:
    processos = inferir_processos(produto, especificacoes)
    return "Arte pendente" if "Criação/ajuste de arte" in processos else "Pronto para produzir"


def normalizar_status_fluxo(status: Any, entregue: bool = False) -> str:
    if entregue:
        return "Entregue"
    mapa_antigo = {
        "A fazer": "Pronto para produzir",
        "Em produção": "Em produção",
        "Aguardando aprovação": "Aguardando aprovação",
        "Pronto": "Pronto",
        "Entregue": "Entregue",
    }
    normalizado = mapa_antigo.get(status, status)
    return normalizado if normalizado in STATUS_FLUXO else "Pedido recebido"


def itens_fluxo_proposta(prop: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Retorna itens operacionais e nunca deixa proposta ativa sem representação."""
    prop = prop or {}
    itens = [dict(i) for i in (prop.get("itens") or []) if isinstance(i, dict)]
    if itens:
        return itens
    nome = str(
        prop.get("produto")
        or prop.get("descricao_produto")
        or prop.get("descricao")
        or "Pedido sem item estruturado"
    ).strip() or "Pedido sem item estruturado"
    return [{
        "produto": nome,
        "quantidade": prop.get("quantidade", 1) or 1,
        "especificacoes": "Registro operacional sem itens estruturados; revisar proposta se necessário.",
        "_fallback_fluxo": True,
    }]


def _adicionar_evento(tarefa: dict[str, Any], descricao: str, now_text: str) -> None:
    timeline = tarefa.get("timeline") if isinstance(tarefa.get("timeline"), list) else []
    timeline.append({"data": now_text, "descricao": descricao})
    tarefa["timeline"] = timeline[-50:]


def reconciliar_lista_fluxo(
    tarefas_base: Iterable[dict[str, Any]] | None,
    propostas_fonte: Iterable[dict[str, Any]] | None,
    *,
    now_text: str,
) -> tuple[list[dict[str, Any]], bool]:
    """Projeta o Fluxo a partir do Histórico oficial preservando campos manuais.

    Função pura: não lê/grava banco e não usa Streamlit. ``now_text`` é recebido
    pelo orquestrador para manter o fuso/configuração do aplicativo.
    """
    tarefas = copy.deepcopy(list(tarefas_base or []))
    existentes = {
        str(t.get("id") or ""): t
        for t in tarefas
        if isinstance(t, dict) and str(t.get("id") or "")
    }
    ids_ativos: set[str] = set()
    alterado = False

    for prop in (propostas_fonte or []):
        if not isinstance(prop, dict) or not proposta_ativa_operacional(prop):
            continue
        numero = str(prop.get("numero_proposta") or "SEM-NUMERO").strip() or "SEM-NUMERO"
        estado_oficial = resumo_status(prop)

        for indice, item in enumerate(itens_fluxo_proposta(prop)):
            tarefa_id = f"{numero}::{indice}"
            ids_ativos.add(tarefa_id)
            produto = str(item.get("produto") or item.get("nome") or "Produto não informado")
            especificacoes = str(item.get("especificacoes") or item.get("detalhes") or "")
            processos = inferir_processos(produto, especificacoes)
            status_inicial = status_inicial_fluxo(produto, especificacoes)
            status_base = (
                "Pronto" if estado_oficial.get("pronto")
                else status_inicial if estado_oficial.get("aprovado")
                else "Pedido recebido"
            )
            base = {
                "id": tarefa_id,
                "numero_proposta": numero,
                "indice_item": indice,
                "cliente_nome": prop.get("cliente_nome", prop.get("cliente", "Cliente não informado")),
                "whatsapp": prop.get("whatsapp", prop.get("cliente_wa", "")),
                "data_entrega": prop.get("data_entrega", ""),
                "produto": produto,
                "especificacoes": especificacoes,
                "quantidade": item.get("quantidade", item.get("qtd", 0)),
                "status": status_base,
                "status_antes_finalizacao": status_inicial if estado_oficial.get("pronto") else "",
                "prioridade": "Normal",
                "processos": processos,
                "necessita_arte": "Criação/ajuste de arte" in processos,
                "observacao_interna": "",
                "timeline": [{"data": now_text, "descricao": "Pedido incluído no fluxo"}],
                "atualizado_em": now_text,
                "origem_espelho": "historico_oficial",
            }
            if item.get("_fallback_fluxo"):
                base["registro_fallback"] = True

            if tarefa_id not in existentes:
                tarefas.append(base)
                existentes[tarefa_id] = base
                alterado = True
                continue

            atual = existentes[tarefa_id]
            for campo in [
                "numero_proposta", "indice_item", "cliente_nome", "whatsapp",
                "data_entrega", "produto", "especificacoes", "quantidade",
            ]:
                if atual.get(campo) != base[campo]:
                    atual[campo] = base[campo]
                    alterado = True
            if atual.get("ativa") is False:
                atual["ativa"] = True
                alterado = True
            if not isinstance(atual.get("processos"), list):
                atual["processos"] = processos
                alterado = True
            if "necessita_arte" not in atual:
                atual["necessita_arte"] = "Criação/ajuste de arte" in atual.get("processos", [])
                alterado = True
            if atual.get("origem_espelho") != "historico_oficial":
                atual["origem_espelho"] = "historico_oficial"
                alterado = True

            status_para_finalizacao = atual.get("status")
            if not estado_oficial.get("pronto"):
                status_aprovacao, status_antes_aprovacao = reconciliar_etapa_aprovacao_oficial(
                    atual.get("status"),
                    estado_oficial.get("aprovado", False),
                    atual.get("status_antes_aprovacao"),
                    status_inicial,
                )
                if status_antes_aprovacao and atual.get("status_antes_aprovacao") != status_antes_aprovacao:
                    atual["status_antes_aprovacao"] = status_antes_aprovacao
                    alterado = True
                if normalizar_status_fluxo(atual.get("status")) != normalizar_status_fluxo(status_aprovacao):
                    _status_antes_hf27 = normalizar_status_fluxo(atual.get("status"))
                    atual["status"] = status_aprovacao
                    _atual_ciclo_hf27 = _aplicar_transicao_ciclo(
                        atual, _status_antes_hf27, status_aprovacao,
                        now_text=now_text, usuario_nome="Sincronização do Fluxo",
                    )
                    atual.clear()
                    atual.update(_atual_ciclo_hf27)
                    _adicionar_evento(
                        atual,
                        "Orçamento aprovado; pedido liberado para a etapa operacional preservada"
                        if estado_oficial.get("aprovado")
                        else "Aprovação comercial removida; pedido voltou a aguardar liberação",
                        now_text,
                    )
                    atual["atualizado_em"] = now_text
                    alterado = True
                status_para_finalizacao = atual.get("status")

            novo_status, status_antes_finalizacao = reconciliar_etapa_status_oficial(
                status_para_finalizacao,
                estado_oficial.get("pronto", False),
                estado_oficial.get("entregue", False),
                atual.get("status_antes_finalizacao") or atual.get("status_antes_entrega"),
            )
            if status_antes_finalizacao and atual.get("status_antes_finalizacao") != status_antes_finalizacao:
                atual["status_antes_finalizacao"] = status_antes_finalizacao
                alterado = True
            if normalizar_status_fluxo(atual.get("status")) != normalizar_status_fluxo(novo_status):
                _status_antes_hf27 = normalizar_status_fluxo(atual.get("status"))
                atual["status"] = novo_status
                _atual_ciclo_hf27 = _aplicar_transicao_ciclo(
                    atual, _status_antes_hf27, novo_status,
                    now_text=now_text, usuario_nome="Sincronização do Fluxo",
                )
                atual.clear()
                atual.update(_atual_ciclo_hf27)
                atual["atualizado_em"] = now_text
                alterado = True
            if not isinstance(atual.get("timeline"), list):
                atual["timeline"] = []
                alterado = True

    for tarefa in tarefas:
        if not isinstance(tarefa, dict):
            continue
        ativa = str(tarefa.get("id") or "") in ids_ativos
        if bool(tarefa.get("ativa", True)) != ativa:
            tarefa["ativa"] = ativa
            alterado = True

    return tarefas, alterado
