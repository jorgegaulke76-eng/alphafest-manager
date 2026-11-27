"""Motor de materiais por pedido — I8.13.2 (Reserva x Consumo Real).

Princípio da versão:
- a necessidade confirmada do pedido pode RESERVAR saldo físico sem movimentá-lo;
- somente o início real da produção gera a baixa física do estoque;
- compras/entradas podem completar reservas pendentes em FIFO;
- movimentos antigos de Pedido continuam válidos como consumo real (compatibilidade).

Este módulo é puro: não conhece Streamlit nem persistência. O app.py grava os
registros e usa estas funções como fonte única de cálculo.
"""
from __future__ import annotations

from typing import Any, Iterable

EPS = 1e-7


def _num(valor: Any) -> float:
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


def _contexto_movimentos(movimentos: Iterable[dict]) -> dict[str, Any]:
    """Indexa movimentos uma vez para os cálculos derivados de materiais.

    HF37: preserva exatamente as regras existentes, mas evita varrer a lista
    inteira de movimentos para cada pedido/material.
    """
    movimentos_l = list(movimentos or [])
    # Inclui também a chave vazia para preservar literalmente a semântica
    # legada de movimento_estornado quando algum movimento não possui id.
    estornados = {
        str((mov or {}).get("estorno_de") or "")
        for mov in movimentos_l
    }
    baixado: dict[tuple[str, str], float] = {}
    for mov in movimentos_l:
        if not isinstance(mov, dict):
            continue
        if str(mov.get("origem_tipo") or "") != "Pedido":
            continue
        origem_id = str(mov.get("origem_id") or "")
        material_id = str(mov.get("material_id") or "")
        delta = _num(mov.get("delta"))
        if delta >= 0:
            continue
        if str(mov.get("id") or "") in estornados:
            continue
        chave = (origem_id, material_id)
        baixado[chave] = baixado.get(chave, 0.0) + abs(delta)
    return {
        "movimentos": movimentos_l,
        "estornados": estornados,
        "baixado": {k: round(v, 6) for k, v in baixado.items()},
    }


def _total_baixado_contexto(contexto: dict[str, Any], consumo_id: str, material_id: str) -> float:
    return round(_num((contexto.get("baixado") or {}).get((str(consumo_id or ""), str(material_id or "")), 0.0)), 6)


def movimento_estornado(movimentos: Iterable[dict], movimento_id: str) -> bool:
    alvo = str(movimento_id or "")
    if not alvo:
        return False
    return alvo in _contexto_movimentos(movimentos).get("estornados", set())


def total_baixado(consumo_id: str, material_id: str, movimentos: Iterable[dict]) -> float:
    """Soma consumo físico ativo do pedido/material, preservando compatibilidade."""
    return _total_baixado_contexto(_contexto_movimentos(movimentos), consumo_id, material_id)


def _reservas_validas(consumo: dict, material_id: str | None = None) -> list[dict]:
    """Reservas persistidas e ainda não liberadas explicitamente."""
    alvo = str(material_id or "")
    resultado = []
    for reserva in (consumo or {}).get("reservas") or []:
        if not isinstance(reserva, dict):
            continue
        if alvo and str(reserva.get("material_id") or "") != alvo:
            continue
        if reserva.get("cancelada_em"):
            continue
        quantidade = max(0.0, _num(reserva.get("quantidade")))
        liberada = max(0.0, _num(reserva.get("quantidade_liberada")))
        disponivel = max(0.0, quantidade - liberada)
        if reserva.get("liberado_em") and disponivel <= EPS:
            continue
        if disponivel <= EPS:
            continue
        resultado.append({**dict(reserva), "quantidade_disponivel": round(disponivel, 6)})
    resultado.sort(key=lambda r: (str(r.get("reservado_em") or ""), str(r.get("id") or "")))
    return resultado


def _reservas_ativas_detalhadas_contexto(consumo: dict, contexto: dict[str, Any], material_id: str) -> list[dict]:
    if not isinstance(consumo, dict) or consumo.get("estornado"):
        return []
    reservas = _reservas_validas(consumo, material_id)
    consumido_restante = max(0.0, _total_baixado_contexto(contexto, consumo.get("id"), material_id))
    ativas = []
    for reserva in reservas:
        qtd = max(0.0, _num(reserva.get("quantidade_disponivel", reserva.get("quantidade"))))
        convertido = min(qtd, consumido_restante)
        consumido_restante = max(0.0, consumido_restante - convertido)
        ativo = max(0.0, qtd - convertido)
        if ativo > EPS:
            ativas.append({**dict(reserva), "quantidade_ativa": round(ativo, 6)})
    return ativas


def reservas_ativas_detalhadas(consumo: dict, movimentos: Iterable[dict], material_id: str) -> list[dict]:
    """Distribui o consumo físico FIFO sobre as reservas e retorna o restante ativo."""
    return _reservas_ativas_detalhadas_contexto(consumo, _contexto_movimentos(movimentos), material_id)


def total_reservado_ativo(consumo: dict, material_id: str, movimentos: Iterable[dict]) -> float:
    contexto = _contexto_movimentos(movimentos)
    return round(sum(_num(r.get("quantidade_ativa")) for r in _reservas_ativas_detalhadas_contexto(consumo, contexto, material_id)), 6)


def reservado_ativo_material(consumos: Iterable[dict], movimentos: Iterable[dict], material_id: str) -> float:
    total = 0.0
    material_id = str(material_id or "")
    contexto = _contexto_movimentos(movimentos)
    for consumo in consumos or []:
        if not isinstance(consumo, dict) or consumo.get("estornado"):
            continue
        total += sum(_num(r.get("quantidade_ativa")) for r in _reservas_ativas_detalhadas_contexto(consumo, contexto, material_id))
    return round(total, 6)


def _resumo_consumo_contexto(consumo: dict, contexto: dict[str, Any]) -> dict:
    """Versão indexada da regra homologada de resumo do consumo."""
    if not isinstance(consumo, dict):
        return {"status": "Sem liberação", "chave": "sem_consumo", "necessidades": [], "pendente": False}
    if consumo.get("estornado"):
        return {"status": "⚪ Estornado", "chave": "estornado", "necessidades": [], "pendente": False}

    linhas = []
    total_necessidades = 0.0
    total_consumido = 0.0
    total_reservado = 0.0
    tem_falta = False
    tem_atendimento = False

    for nec in consumo.get("necessidades") or []:
        material_id = str((nec or {}).get("material_id") or "")
        necessario = max(0.0, _num((nec or {}).get("necessario")))
        consumido = min(necessario, _total_baixado_contexto(contexto, consumo.get("id"), material_id))
        falta_apos_consumo = max(0.0, necessario - consumido)
        reservado = min(
            falta_apos_consumo,
            round(sum(_num(r.get("quantidade_ativa")) for r in _reservas_ativas_detalhadas_contexto(consumo, contexto, material_id)), 6),
        )
        pendente = max(0.0, necessario - consumido - reservado)

        total_necessidades += necessario
        total_consumido += consumido
        total_reservado += reservado
        tem_atendimento = tem_atendimento or consumido > EPS or reservado > EPS
        tem_falta = tem_falta or pendente > EPS
        linhas.append({
            **dict(nec or {}),
            "necessario": round(necessario, 6),
            "baixado": round(consumido, 6),
            "consumido": round(consumido, 6),
            "reservado": round(reservado, 6),
            "pendente": round(pendente, 6),
            "falta_reserva": round(pendente, 6),
        })

    if not linhas:
        status, chave, fase = "⚪ Sem materiais", "sem_materiais", "sem_materiais"
    elif not tem_falta:
        if total_reservado > EPS:
            status, chave, fase = "🔒 Materiais reservados", "atendido", "reservado"
        else:
            status, chave, fase = "🟢 Materiais consumidos", "atendido", "consumido"
    elif tem_atendimento:
        status, chave, fase = "🟡 Parcialmente reservado", "parcial", "parcial"
    else:
        status, chave, fase = "🟠 Falta material para reservar", "pendente", "pendente"

    return {
        "status": status,
        "chave": chave,
        "fase_material": fase,
        "necessidades": linhas,
        "pendente": tem_falta,
        "total_necessidades": round(total_necessidades, 6),
        "total_baixas": round(total_consumido, 6),
        "total_consumido": round(total_consumido, 6),
        "total_reservado": round(total_reservado, 6),
        "total_pendente": round(sum(_num(n.get("pendente")) for n in linhas), 6),
    }


def resumo_consumo(consumo: dict, movimentos: Iterable[dict]) -> dict:
    """Deriva Necessário / Reservado / Consumido / Falta do pedido."""
    return _resumo_consumo_contexto(consumo, _contexto_movimentos(movimentos))


def resumos_consumos(consumos: Iterable[dict], movimentos: Iterable[dict]) -> list[tuple[dict, dict]]:
    """Resume uma coleção inteira reutilizando um único índice de movimentos."""
    contexto = _contexto_movimentos(movimentos)
    resultado: list[tuple[dict, dict]] = []
    for consumo in consumos or []:
        if not isinstance(consumo, dict):
            continue
        resultado.append((consumo, _resumo_consumo_contexto(consumo, contexto)))
    return resultado


def pendencia_material(consumos: Iterable[dict], movimentos: Iterable[dict], material_id: str) -> float:
    """Falta real não coberta por consumo nem reserva."""
    total = 0.0
    material_id = str(material_id or "")
    for consumo, resumo in resumos_consumos(consumos, movimentos):
        if consumo.get("estornado"):
            continue
        for nec in resumo.get("necessidades") or []:
            if str((nec or {}).get("material_id") or "") == material_id:
                total += _num((nec or {}).get("pendente"))
    return round(total, 6)


def totais_materiais(consumos: Iterable[dict], movimentos: Iterable[dict]) -> dict[str, dict[str, float]]:
    """Agrega reserva ativa e falta real de todos os materiais em uma passagem.

    ``reservado`` preserva a mesma regra de ``reservado_ativo_material`` (reserva
    física ativa, inclusive eventual excedente). ``pendente`` preserva a falta
    derivada de ``resumo_consumo``.
    """
    consumos_l = [c for c in (consumos or []) if isinstance(c, dict) and not c.get("estornado")]
    contexto = _contexto_movimentos(movimentos)
    totais: dict[str, dict[str, float]] = {}
    for consumo in consumos_l:
        ids = {
            str((n or {}).get("material_id") or "")
            for n in (consumo.get("necessidades") or [])
            if str((n or {}).get("material_id") or "")
        }
        ids.update(
            str((r or {}).get("material_id") or "")
            for r in (consumo.get("reservas") or [])
            if str((r or {}).get("material_id") or "")
        )
        for material_id in ids:
            reservado = sum(
                _num(r.get("quantidade_ativa"))
                for r in _reservas_ativas_detalhadas_contexto(consumo, contexto, material_id)
            )
            if reservado > EPS:
                linha = totais.setdefault(material_id, {"reservado": 0.0, "pendente": 0.0})
                linha["reservado"] = round(_num(linha.get("reservado")) + reservado, 6)

        resumo = _resumo_consumo_contexto(consumo, contexto)
        for nec in resumo.get("necessidades") or []:
            material_id = str((nec or {}).get("material_id") or "")
            if not material_id:
                continue
            pendente = max(0.0, _num((nec or {}).get("pendente")))
            linha = totais.setdefault(material_id, {"reservado": 0.0, "pendente": 0.0})
            linha["pendente"] = round(_num(linha.get("pendente")) + pendente, 6)
    return totais


def planejar_reducao_reservas(consumos: Iterable[dict], movimentos: Iterable[dict], saldos: dict[str, float]) -> list[dict]:
    """Libera reservas mais novas se uma perda/ajuste deixou o físico insuficiente.

    Pedidos mais antigos preservam prioridade. O retorno descreve apenas o que
    o app deve marcar como liberado; não movimenta estoque.
    """
    movimentos = list(movimentos or [])
    contexto = _contexto_movimentos(movimentos)
    consumos = [c for c in (consumos or []) if isinstance(c, dict) and not c.get("estornado")]
    ativos_por_material: dict[str, list[dict]] = {}
    for consumo in consumos:
        ids = {str((n or {}).get("material_id") or "") for n in consumo.get("necessidades") or []}
        for material_id in ids:
            if not material_id:
                continue
            for reserva in _reservas_ativas_detalhadas_contexto(consumo, contexto, material_id):
                ativos_por_material.setdefault(material_id, []).append({
                    "consumo_id": str(consumo.get("id") or ""),
                    "numero_proposta": str(consumo.get("numero_proposta") or ""),
                    "reserva_id": str(reserva.get("id") or ""),
                    "material_id": material_id,
                    "material_nome": str(reserva.get("material_nome") or ""),
                    "unidade": str(reserva.get("unidade") or ""),
                    "quantidade_ativa": max(0.0, _num(reserva.get("quantidade_ativa"))),
                    "reservado_em": str(reserva.get("reservado_em") or ""),
                })

    plano: list[dict] = []
    for material_id, reservas in ativos_por_material.items():
        fisico = max(0.0, _num((saldos or {}).get(material_id)))
        total_reservado = sum(_num(r.get("quantidade_ativa")) for r in reservas)
        excesso = max(0.0, total_reservado - fisico)
        if excesso <= EPS:
            continue
        # LIFO: a reserva mais nova cede primeiro, preservando FIFO dos pedidos.
        reservas.sort(key=lambda r: (r.get("reservado_em") or "", r.get("reserva_id") or ""), reverse=True)
        for reserva in reservas:
            if excesso <= EPS:
                break
            liberar = min(excesso, max(0.0, _num(reserva.get("quantidade_ativa"))))
            if liberar <= EPS:
                continue
            plano.append({**reserva, "quantidade": round(liberar, 6)})
            excesso = max(0.0, excesso - liberar)
    return plano


def planejar_regularizacao(consumos: Iterable[dict], movimentos: Iterable[dict], saldos: dict[str, float]) -> list[dict]:
    """Planeja novas RESERVAS FIFO usando somente saldo físico livre.

    O saldo livre = saldo físico - reservas ativas já existentes. Nenhuma baixa
    física é proposta nesta etapa.
    """
    movimentos = list(movimentos or [])
    contexto = _contexto_movimentos(movimentos)
    ativos = [c for c in (consumos or []) if isinstance(c, dict) and not c.get("estornado")]
    ativos.sort(key=lambda c: (str(c.get("confirmado_em") or ""), str(c.get("id") or "")))

    resumos_por_id = {str(c.get("id") or ""): _resumo_consumo_contexto(c, contexto) for c in ativos}
    reservados_globais: dict[str, float] = {}
    for consumo in ativos:
        resumo = resumos_por_id.get(str(consumo.get("id") or ""), {})
        for nec in resumo.get("necessidades") or []:
            mid = str(nec.get("material_id") or "")
            reservados_globais[mid] = round(reservados_globais.get(mid, 0.0) + _num(nec.get("reservado")), 6)

    saldos_trabalho = {
        str(k): max(0.0, _num(v) - reservados_globais.get(str(k), 0.0))
        for k, v in (saldos or {}).items()
    }

    plano = []
    for consumo in ativos:
        resumo = resumos_por_id.get(str(consumo.get("id") or ""), {})
        for nec in resumo.get("necessidades") or []:
            material_id = str(nec.get("material_id") or "")
            pendente = max(0.0, _num(nec.get("pendente")))
            disponivel = max(0.0, saldos_trabalho.get(material_id, 0.0))
            reservar = min(disponivel, pendente)
            if reservar <= EPS:
                continue
            plano.append({
                "consumo_id": str(consumo.get("id") or ""),
                "numero_proposta": str(consumo.get("numero_proposta") or ""),
                "material_id": material_id,
                "material_nome": str(nec.get("material_nome") or ""),
                "unidade": str(nec.get("unidade") or ""),
                "quantidade": round(reservar, 6),
            })
            saldos_trabalho[material_id] = round(disponivel - reservar, 6)
    return plano
