"""Motor puro da I8.12.8-HF2 — Central de Produção.

A Central não cria uma nova fonte de pedido, estoque ou produção. Ela combina:
- a previsão material/prazo da I8.12.7;
- o andamento manual já existente em ``producao_db`` (Fluxo de Pedidos).

O objetivo é oferecer uma fila operacional única para Jorge e Anna sem gravar
um status derivado paralelo. Somente as etapas manuais do Fluxo continuam sendo
persistidas em ``producao_db``.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable


_STATUS_PREPARACAO = {"Pedido recebido", "Arte pendente", "Aguardando aprovação"}
_STATUS_PRONTO_INICIAR = {"Pronto para produzir"}
_STATUS_EM_PRODUCAO = {"Em produção"}
_STATUS_PRONTO = {"Pronto", "Entregue"}


def _bool(valor: Any) -> bool:
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return bool(valor)
    return str(valor or "").strip().casefold() in {
        "1", "true", "sim", "yes", "ok", "pago", "aprovado", "pronto", "entregue"
    }


def _normalizar_status(status: Any) -> str:
    texto = str(status or "").strip()
    mapa = {
        "A fazer": "Pronto para produzir",
        "Arte em desenvolvimento": "Arte pendente",
        "Arte aprovada": "Pronto para produzir",
        "Montagem/acabamento": "Em produção",
    }
    return mapa.get(texto, texto or "Pedido recebido")


def reconciliar_etapa_status_oficial(
    status_manual: Any,
    pronto_oficial: Any,
    entregue_oficial: Any,
    status_antes_finalizacao: Any = None,
) -> tuple[str, str]:
    """Espelha Pronto/Entregue oficiais sem dar ao producao_db o status do pedido.

    A etapa anterior é preservada para permitir correções: desmarcar Entregue
    mantém Pronto; desmarcar Pronto restaura a etapa anterior de produção.
    """
    atual = _normalizar_status(status_manual)
    anterior = _normalizar_status(status_antes_finalizacao) if str(status_antes_finalizacao or "").strip() else ""
    entregue = _bool(entregue_oficial)
    pronto = _bool(pronto_oficial) or entregue
    if entregue:
        if atual not in {"Pronto", "Entregue"}:
            anterior = atual
        return "Entregue", anterior
    if pronto:
        if atual not in {"Pronto", "Entregue"}:
            anterior = atual
        return "Pronto", anterior
    if atual in {"Pronto", "Entregue"}:
        restaurar = _normalizar_status(anterior or "Pronto para produzir")
        if restaurar in {"Pronto", "Entregue"}:
            restaurar = "Pronto para produzir"
        return restaurar, anterior
    return atual, anterior


def reconciliar_etapa_aprovacao_oficial(
    status_manual: Any,
    aprovado_oficial: Any,
    status_antes_aprovacao: Any = None,
    status_inicial: Any = "Pronto para produzir",
) -> tuple[str, str]:
    """I8.13.4-HF2 — reconcilia liberação comercial com a etapa manual.

    Antes da aprovação oficial, o item permanece em ``Pedido recebido`` e não
    entra artificialmente em arte/produção. Se uma aprovação já existente for
    removida, a etapa manual anterior é preservada; ao aprovar novamente, ela
    é restaurada. ``Aguardando aprovação`` continua reservado à aprovação de
    ARTE dentro do Fluxo e não é confundido com aprovação comercial.
    """
    atual = _normalizar_status(status_manual)
    anterior = _normalizar_status(status_antes_aprovacao) if str(status_antes_aprovacao or "").strip() else ""
    aprovado = _bool(aprovado_oficial)

    if not aprovado:
        if atual not in {"Pedido recebido", "Pronto", "Entregue"}:
            anterior = atual
        if atual in {"Pronto", "Entregue"}:
            return atual, anterior
        return "Pedido recebido", anterior

    if atual == "Pedido recebido":
        restaurar = _normalizar_status(anterior or status_inicial or "Pronto para produzir")
        if restaurar in {"Pedido recebido", "Pronto", "Entregue"}:
            restaurar = _normalizar_status(status_inicial or "Pronto para produzir")
        if restaurar == "Pedido recebido":
            restaurar = "Pronto para produzir"
        return restaurar, anterior

    return atual, anterior


def reconciliar_etapa_entrega(status_manual: Any, entregue_oficial: Any, status_antes_entrega: Any = None) -> tuple[str, str]:
    """Compatibilidade com a assinatura da HF1."""
    return reconciliar_etapa_status_oficial(status_manual, False, entregue_oficial, status_antes_entrega)


def _data(valor: Any) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor or "").strip()
    if not texto:
        return None
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto[:10], formato).date()
        except Exception:
            pass
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")).date()
    except Exception:
        return None


def _prioridade_manual(tarefas: list[dict]) -> tuple[str, int]:
    ranking = {"Urgente": 0, "Alta": 1, "Normal": 2, "Baixa": 3}
    candidatos = [str(t.get("prioridade") or "Normal") for t in tarefas]
    candidatos = [p for p in candidatos if p in ranking] or ["Normal"]
    escolhida = min(candidatos, key=lambda p: ranking[p])
    return escolhida, ranking[escolhida]


def _etapa_manual(tarefas: list[dict]) -> tuple[str, str]:
    """Retorna (chave, rótulo) da etapa manual agregada do pedido."""
    if not tarefas:
        return "sem_registro", "⚪ Aguardando etapa no Fluxo"
    statuses = [_normalizar_status(t.get("status")) for t in tarefas]
    if all(s in _STATUS_PRONTO for s in statuses):
        return "pronto", "✅ Pronto para entrega"
    if any(s in _STATUS_EM_PRODUCAO for s in statuses):
        return "em_producao", "🔵 Em produção"
    if any(s in _STATUS_PREPARACAO for s in statuses):
        return "preparacao", "🎨 Preparação / arte"
    if any(s in _STATUS_PRONTO_INICIAR for s in statuses):
        return "fila", "🟢 Pronto para iniciar"
    return "preparacao", "🎨 Preparação / arte"


def montar_central_producao(
    previsoes: Iterable[dict],
    tarefas: Iterable[dict],
    hoje: date | None = None,
) -> list[dict]:
    """Combina previsão I8.12.7 e Fluxo manual em uma fila operacional.

    A entrada ``previsoes`` já deve conter somente propostas aprovadas e ainda
    não entregues. A função não persiste nada e não altera as fontes recebidas.
    """
    hoje = hoje or date.today()
    tarefas_validas = [t for t in (tarefas or []) if isinstance(t, dict) and t.get("ativa", True)]
    por_pedido: dict[str, list[dict]] = {}
    for tarefa in tarefas_validas:
        numero = str(tarefa.get("numero_proposta") or "").strip()
        if numero:
            por_pedido.setdefault(numero, []).append(tarefa)

    resultado: list[dict] = []
    for previsao in previsoes or []:
        if not isinstance(previsao, dict):
            continue
        numero = str(previsao.get("numero_proposta") or "").strip()
        if not numero:
            continue
        itens = por_pedido.get(numero, [])
        etapa_chave, etapa = _etapa_manual(itens)
        prioridade, prioridade_rank = _prioridade_manual(itens)
        chave_material = str(previsao.get("chave_base") or previsao.get("chave") or "")
        material_liberado = chave_material == "liberado"
        risco = _bool(previsao.get("risco_atraso")) or str(previsao.get("chave") or "") == "risco_atraso"

        statuses = [_normalizar_status(t.get("status")) for t in itens]
        pode_iniciar = bool(
            material_liberado
            and statuses
            and any(s in _STATUS_PRONTO_INICIAR for s in statuses)
            and all(s in (_STATUS_PRONTO_INICIAR | _STATUS_EM_PRODUCAO | _STATUS_PRONTO) for s in statuses)
        )
        pode_marcar_pronto = bool(
            material_liberado
            and statuses
            and any(s in _STATUS_EM_PRODUCAO for s in statuses)
            and all(s in (_STATUS_EM_PRODUCAO | _STATUS_PRONTO) for s in statuses)
        )

        if chave_material == "pronto_aguardando_entrega" or _bool(previsao.get("pronto_oficial")):
            situacao = "📦 Pronto — aguardando retirada/entrega"
            situacao_chave = "pronto_entrega"
            proxima_acao = "Retirar/entregar ao cliente"
            pode_iniciar = False
            pode_marcar_pronto = False
        elif chave_material == "aguardando_liberacao":
            situacao = "⚪ Aguardando liberação de materiais"
            situacao_chave = "aguardando_liberacao"
            proxima_acao = "Confirmar e reservar materiais"
        elif chave_material == "aguardando_material":
            situacao = "🟠 Aguardando material"
            situacao_chave = "aguardando_material"
            proxima_acao = "Comprar ou receber material"
        elif chave_material == "compra_em_andamento":
            situacao = "🛒 Compra em andamento"
            situacao_chave = "compra_em_andamento"
            proxima_acao = "Acompanhar recebimento do fornecedor"
        elif etapa_chave == "sem_registro":
            situacao = etapa
            situacao_chave = "sem_registro"
            proxima_acao = "Abrir Fluxo de Pedidos e conferir etapa"
        elif etapa_chave == "preparacao":
            situacao = etapa
            situacao_chave = "preparacao"
            proxima_acao = "Concluir arte / preparação"
        elif etapa_chave == "fila":
            situacao = etapa
            situacao_chave = "pronto_iniciar"
            proxima_acao = "Iniciar produção"
        elif etapa_chave == "em_producao":
            situacao = etapa
            situacao_chave = "em_producao"
            proxima_acao = "Concluir produção"
        elif etapa_chave == "pronto":
            situacao = etapa
            situacao_chave = "pronto_entrega"
            proxima_acao = "Preparar / registrar entrega"
        else:
            situacao = etapa
            situacao_chave = etapa_chave
            proxima_acao = "Revisar Fluxo de Pedidos"

        entrega = previsao.get("data_entrega")
        entrega = entrega if isinstance(entrega, date) else _data(entrega or previsao.get("data_entrega_original"))
        dias = (entrega - hoje).days if isinstance(entrega, date) else 999999

        linha = dict(previsao)
        linha.update({
            "tarefas": itens,
            "quantidade_itens_fluxo": len(itens),
            "etapa_manual": etapa,
            "etapa_manual_chave": etapa_chave,
            "situacao_operacional": situacao,
            "situacao_operacional_chave": situacao_chave,
            "proxima_acao_producao": proxima_acao,
            "material_liberado": material_liberado,
            "pode_iniciar_producao": pode_iniciar,
            "pode_marcar_pronto": pode_marcar_pronto,
            "prioridade_manual": prioridade,
            "prioridade_manual_rank": prioridade_rank,
            "tem_etapa_manual": bool(itens),
            "fonte_status_pedido": "proposta_oficial",
            "fonte_material_prazo": "I8.12.7",
            "fonte_etapa_producao": "producao_db",
            "risco_atraso": risco,
            "dias_ate_entrega": dias if dias != 999999 else previsao.get("dias_ate_entrega"),
        })
        resultado.append(linha)

    # Prazo e risco dominam a fila; a prioridade manual desempata pedidos da
    # mesma janela sem sobrescrever a data de entrega informada pelo usuário.
    resultado.sort(key=lambda p: (
        0 if p.get("risco_atraso") else 1,
        p.get("data_entrega") if isinstance(p.get("data_entrega"), date) else date.max,
        int(p.get("prioridade_manual_rank", 9)),
        str(p.get("confirmado_em") or ""),
        str(p.get("numero_proposta") or ""),
    ))
    return resultado


def resumo_central(linhas: Iterable[dict]) -> dict[str, int]:
    linhas = [l for l in (linhas or []) if isinstance(l, dict)]
    return {
        "total": len(linhas),
        "risco": sum(1 for l in linhas if l.get("risco_atraso")),
        "prontos_iniciar": sum(1 for l in linhas if l.get("situacao_operacional_chave") == "pronto_iniciar"),
        "em_producao": sum(1 for l in linhas if l.get("situacao_operacional_chave") == "em_producao"),
        "prontos_entrega": sum(1 for l in linhas if l.get("situacao_operacional_chave") == "pronto_entrega"),
        "bloqueados_material": sum(1 for l in linhas if l.get("situacao_operacional_chave") in {"aguardando_liberacao", "aguardando_material", "compra_em_andamento"}),
        "preparacao": sum(1 for l in linhas if l.get("situacao_operacional_chave") == "preparacao"),
        "sem_registro": sum(1 for l in linhas if l.get("situacao_operacional_chave") == "sem_registro"),
    }
