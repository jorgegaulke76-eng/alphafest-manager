"""Motor puro da I8.12.7-HF1 — Previsão de Produção e Risco de Entrega.

A previsão não cria uma nova fonte operacional. Ela deriva o estado de pedidos
aprovados ainda não entregues a partir de três fontes já oficiais:
- consumo confirmado / pendências de materiais (I8.12.4);
- movimentações de estoque;
- planejamento de compras em aberto (I8.12.6).

O motor não estima tempo de fabricação. O risco considera somente data de
entrega, disponibilidade material e previsão informada ao fornecedor.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable

from consumo_estoque_engine import resumo_consumo
from planejamento_compras_engine import quantidade_aberta


def _num(valor: Any) -> float:
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


def _bool(valor: Any) -> bool:
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return bool(valor)
    return str(valor or "").strip().casefold() in {
        "1", "true", "sim", "yes", "ok", "pago", "aprovado", "entregue"
    }


def _status(proposta: dict, campo: str) -> Any:
    if campo in proposta:
        return proposta.get(campo)
    legado = {"aprovado": "Aprovado", "entregue": "Entregue"}.get(campo)
    return proposta.get(legado) if legado else None


def _data(valor: Any) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor or "").strip()
    if not texto:
        return None
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(texto[:19] if "%H" in formato else texto[:10], formato).date()
        except Exception:
            pass
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")).date()
    except Exception:
        return None


def _consumo_ativo_por_pedido(consumos: Iterable[dict]) -> dict[str, dict]:
    mapa: dict[str, dict] = {}
    for consumo in consumos or []:
        if not isinstance(consumo, dict) or consumo.get("estornado"):
            continue
        numero = str(consumo.get("numero_proposta") or "").strip()
        if not numero:
            continue
        atual = mapa.get(numero)
        if atual is None or (str(consumo.get("confirmado_em") or ""), str(consumo.get("id") or "")) > (
            str(atual.get("confirmado_em") or ""), str(atual.get("id") or "")
        ):
            mapa[numero] = consumo
    return mapa


def _planos_abertos_por_material(planos: Iterable[dict]) -> dict[str, list[dict]]:
    mapa: dict[str, list[dict]] = {}
    for plano in planos or []:
        if not isinstance(plano, dict):
            continue
        aberto = max(0.0, quantidade_aberta(plano))
        material_id = str(plano.get("material_id") or "").strip()
        if aberto <= 1e-7 or not material_id:
            continue
        mapa.setdefault(material_id, []).append({
            "plano": plano,
            "restante": aberto,
            "previsao": _data(plano.get("previsao_recebimento")),
        })
    for material_id in mapa:
        mapa[material_id].sort(key=lambda x: (
            x.get("previsao") or date.max,
            str((x.get("plano") or {}).get("criado_em") or ""),
            str((x.get("plano") or {}).get("id") or ""),
        ))
    return mapa


def montar_previsao_producao(
    propostas: Iterable[dict],
    consumos: Iterable[dict],
    movimentos: Iterable[dict],
    planejamentos: Iterable[dict],
    hoje: date | None = None,
) -> list[dict]:
    """Classifica pedidos aprovados e ainda não entregues usando fontes oficiais.

    Regras principais:
    - sem consumo confirmado: aguardando liberação de materiais;
    - sem pendência: liberado para produção;
    - falta totalmente coberta por solicitação aberta: compra em andamento;
    - falta não coberta: aguardando material;
    - risco de atraso tem precedência quando o prazo já venceu, quando material
      ainda indisponível chega no máximo amanhã, ou quando a previsão de compra
      informada ultrapassa a entrega.

    A quantidade em compra é alocada FIFO entre pedidos pendentes do mesmo
    material para evitar que uma única solicitação pareça cobrir vários pedidos
    ao mesmo tempo.
    """
    hoje = hoje or date.today()
    propostas_validas = [p for p in (propostas or []) if isinstance(p, dict)]
    consumo_por_pedido = _consumo_ativo_por_pedido(consumos or [])
    movimentos = list(movimentos or [])

    # Primeiro deriva cada pendência, ordenando pedidos por confirmação para a
    # alocação FIFO das solicitações abertas ao fornecedor.
    base: list[dict] = []
    for proposta in propostas_validas:
        numero = str(proposta.get("numero_proposta") or "").strip()
        if not numero or not _bool(_status(proposta, "aprovado")) or _bool(_status(proposta, "entregue")):
            continue
        entrega = _data(proposta.get("data_entrega"))
        dias = (entrega - hoje).days if entrega else None
        consumo = consumo_por_pedido.get(numero)
        resumo = resumo_consumo(consumo, movimentos) if consumo else None
        necessidades = list((resumo or {}).get("necessidades") or [])
        pendentes = [dict(n) for n in necessidades if max(0.0, _num((n or {}).get("pendente"))) > 1e-7]
        base.append({
            "numero_proposta": numero,
            "cliente_nome": str(proposta.get("cliente_nome") or "Cliente"),
            "data_entrega": entrega,
            "data_entrega_original": proposta.get("data_entrega"),
            "dias_ate_entrega": dias,
            "consumo": consumo,
            "resumo_consumo": resumo,
            "pendencias": pendentes,
            "materiais": necessidades,
            "confirmado_em": str((consumo or {}).get("confirmado_em") or ""),
        })

    # Aloca compras abertas por material aos pedidos mais antigos primeiro.
    planos_por_material = _planos_abertos_por_material(planejamentos or [])
    demandas_por_material: dict[str, list[tuple[dict, dict]]] = {}
    for pedido in base:
        for nec in pedido.get("pendencias") or []:
            material_id = str(nec.get("material_id") or "").strip()
            if material_id:
                demandas_por_material.setdefault(material_id, []).append((pedido, nec))
    for material_id, demandas in demandas_por_material.items():
        demandas.sort(key=lambda par: (
            str(par[0].get("confirmado_em") or ""),
            str(par[0].get("numero_proposta") or ""),
        ))
        planos_mat = planos_por_material.get(material_id, [])
        for pedido, nec in demandas:
            pendente = max(0.0, _num(nec.get("pendente")))
            coberto = 0.0
            previsoes_usadas: list[date] = []
            sem_previsao = False
            planos_usados: list[str] = []
            faltante = pendente
            for slot in planos_mat:
                if faltante <= 1e-7:
                    break
                disponivel = max(0.0, _num(slot.get("restante")))
                if disponivel <= 1e-7:
                    continue
                alocar = min(disponivel, faltante)
                slot["restante"] = round(disponivel - alocar, 6)
                faltante = round(faltante - alocar, 6)
                coberto += alocar
                plano = slot.get("plano") or {}
                if str(plano.get("id") or ""):
                    planos_usados.append(str(plano.get("id") or ""))
                if slot.get("previsao"):
                    previsoes_usadas.append(slot["previsao"])
                else:
                    sem_previsao = True
            nec["quantidade_em_compra_alocada"] = round(coberto, 6)
            nec["quantidade_sem_cobertura"] = round(max(0.0, pendente - coberto), 6)
            nec["previsao_cobertura"] = max(previsoes_usadas) if previsoes_usadas and not sem_previsao and coberto + 1e-7 >= pendente else None
            nec["compra_sem_previsao"] = bool(sem_previsao and coberto > 1e-7)
            nec["planos_alocados"] = planos_usados

    resultado: list[dict] = []
    for pedido in base:
        entrega = pedido.get("data_entrega")
        dias = pedido.get("dias_ate_entrega")
        consumo = pedido.get("consumo")
        pendencias = pedido.get("pendencias") or []
        motivos: list[str] = []
        risco = False

        if not consumo:
            chave_base = "aguardando_liberacao"
            status_base = "⚪ Aguardando liberação de materiais"
            # HF1: antes da liberação não existe apuração física oficial. Nunca
            # comunicar "sem falta" ou "materiais atendidos" neste estado.
            if isinstance(dias, int) and dias < 0:
                risco = True
                motivos.append(f"entrega vencida há {abs(dias)} dia(s) e consumo ainda não foi liberado")
            elif isinstance(dias, int) and dias <= 1:
                motivos.append("entrega muito próxima e consumo ainda não foi liberado")
            motivos.append("confirmar liberação de consumo para verificar disponibilidade dos materiais")
        elif not pendencias:
            chave_base = "liberado"
            status_base = "🟢 Liberado para produção"
            if isinstance(dias, int) and dias < 0:
                risco = True
                motivos.append(f"entrega vencida há {abs(dias)} dia(s)")
        else:
            total_pendente = sum(max(0.0, _num(n.get("pendente"))) for n in pendencias)
            total_sem_cobertura = sum(max(0.0, _num(n.get("quantidade_sem_cobertura"))) for n in pendencias)
            total_coberto = sum(max(0.0, _num(n.get("quantidade_em_compra_alocada"))) for n in pendencias)
            if total_sem_cobertura <= 1e-7 and total_coberto > 1e-7:
                chave_base = "compra_em_andamento"
                status_base = "🛒 Compra em andamento"
            else:
                chave_base = "aguardando_material"
                status_base = "🟠 Aguardando material"

            if isinstance(dias, int) and dias < 0:
                risco = True
                motivos.append(f"entrega vencida há {abs(dias)} dia(s) com material pendente")
            elif isinstance(dias, int) and dias <= 1:
                risco = True
                motivos.append("entrega é hoje/amanhã e ainda há material pendente")
            if isinstance(entrega, date):
                atrasadas = [n for n in pendencias if isinstance(n.get("previsao_cobertura"), date) and n.get("previsao_cobertura") > entrega]
                if atrasadas:
                    risco = True
                    motivos.append("previsão informada de compra ultrapassa a data de entrega")
            if total_sem_cobertura > 1e-7:
                motivos.append("há material ainda sem cobertura de compra")
            elif any(bool(n.get("compra_sem_previsao")) for n in pendencias):
                motivos.append("compra aberta sem previsão de recebimento informada")
            elif total_pendente > 1e-7:
                motivos.append("material ainda não foi recebido fisicamente")

        if risco:
            chave = "risco_atraso"
            status = "🔴 Risco de atraso"
            severidade = 0
        else:
            chave = chave_base
            status = status_base
            severidade = {
                "aguardando_material": 1,
                "compra_em_andamento": 2,
                "aguardando_liberacao": 3,
                "liberado": 4,
            }.get(chave_base, 5)

        pedido["status_base"] = status_base
        pedido["chave_base"] = chave_base
        pedido["status"] = status
        pedido["chave"] = chave
        pedido["risco_atraso"] = risco
        pedido["motivos"] = motivos
        pedido["severidade"] = severidade
        pedido["quantidade_materiais_pendentes"] = len(pendencias)
        pedido["quantidade_materiais_sem_cobertura"] = sum(1 for n in pendencias if _num(n.get("quantidade_sem_cobertura")) > 1e-7)
        resultado.append(pedido)

    resultado.sort(key=lambda p: (
        int(p.get("severidade", 9)),
        p.get("data_entrega") or date.max,
        str(p.get("numero_proposta") or ""),
    ))
    return resultado
