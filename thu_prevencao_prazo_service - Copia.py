"""20.4.9-I8.13.5-HF25 — prevenção assistida de prazo/carga do THU.

Este módulo é somente leitura. Ele não calcula uma "capacidade de fábrica" exata,
pois o AlphaFest Manager ainda não possui tempo produtivo padronizado por item.
Em vez disso, identifica *pressão de janela* usando dados já oficiais:
- data de entrega;
- prazo de produção informado na proposta;
- estágio atual da Central de Produção;
- bloqueio/liberação de materiais;
- concentração de pedidos ainda não Prontos na mesma data.

O objetivo é avisar antes de o pedido entrar nas faixas críticas da I8.13.1.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
import re
from typing import Any, Iterable

from proposal_status import resumo_status


_BLOQUEIOS = {"aguardando_liberacao", "aguardando_material", "compra_em_andamento"}
_NAO_INICIADOS = _BLOQUEIOS | {"sem_registro", "preparacao", "pronto_iniciar"}


def _data(valor: Any) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor or "").strip()
    if not texto:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            alvo = texto[:19] if "%H" in fmt else texto[:10]
            return datetime.strptime(alvo, fmt).date()
        except Exception:
            pass
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")).date()
    except Exception:
        return None


def _prazo_producao(valor: Any) -> int | None:
    """Extrai um prazo inteiro razoável sem inventar valor quando o campo é livre."""
    texto = str(valor or "").strip()
    if not texto:
        return None
    m = re.search(r"\d+", texto)
    if not m:
        return None
    try:
        dias = int(m.group(0))
    except Exception:
        return None
    return dias if 1 <= dias <= 90 else None


def _dias_uteis_restantes(hoje: date, entrega: date) -> int:
    """Conta dias úteis depois de hoje até a entrega, inclusive a data final."""
    if entrega <= hoje:
        return 0
    atual = hoje + timedelta(days=1)
    total = 0
    while atual <= entrega:
        if atual.weekday() < 5:
            total += 1
        atual += timedelta(days=1)
    return total


def _indexar(linhas: Iterable[dict] | None) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for linha in linhas or []:
        if not isinstance(linha, dict):
            continue
        numero = str(linha.get("numero_proposta") or "").strip()
        if numero:
            out[numero] = linha
    return out


def montar_sinais_prevencao_prazo(
    propostas: Iterable[dict] | None,
    hoje: date,
    *,
    central_producao: Iterable[dict] | None = None,
    limite: int = 12,
    horizonte_dias: int = 10,
) -> list[dict[str, Any]]:
    """Retorna sinais preventivos para pedidos futuros ainda não Prontos.

    Pedidos com entrega em até 2 dias ficam de fora porque já pertencem às
    prioridades operacionais concretas da I8.13.1. O radar olha principalmente
    a janela de 3 a ``horizonte_dias`` dias.
    """
    hoje = hoje or date.today()
    producao = _indexar(central_producao)
    candidatos: list[tuple[dict, date, int]] = []

    for proposta in propostas or []:
        if not isinstance(proposta, dict):
            continue
        estado = resumo_status(proposta)
        if not estado.get("aprovado") or not estado.get("ativa") or estado.get("pronto") or estado.get("entregue"):
            continue
        numero = str(proposta.get("numero_proposta") or "").strip()
        entrega = _data(proposta.get("data_entrega"))
        if not numero or entrega is None:
            continue
        dias = (entrega - hoje).days
        if dias < 3 or dias > max(3, int(horizonte_dias or 10)):
            continue
        candidatos.append((proposta, entrega, dias))

    # Pressão de agenda: quantidade de pedidos ainda não Prontos concentrados
    # na mesma data. É um sinal qualitativo, não uma afirmação de capacidade.
    carga_por_data: dict[date, int] = {}
    for _, entrega, _ in candidatos:
        carga_por_data[entrega] = carga_por_data.get(entrega, 0) + 1

    sinais: list[dict[str, Any]] = []
    for proposta, entrega, dias in candidatos:
        numero = str(proposta.get("numero_proposta") or "").strip()
        prod = producao.get(numero, {})
        etapa = str(prod.get("situacao_operacional_chave") or "sem_registro").strip() or "sem_registro"
        etapa_rotulo = str(prod.get("situacao_operacional") or "⚪ Aguardando etapa no Fluxo").strip()
        prazo = _prazo_producao(proposta.get("prazo_dias"))
        uteis = _dias_uteis_restantes(hoje, entrega)
        carga = int(carga_por_data.get(entrega, 1))
        bloqueado = etapa in _BLOQUEIOS
        nao_iniciado = etapa in _NAO_INICIADOS
        janela_apertada = bool(prazo and nao_iniciado and uteis <= prazo)
        preparacao_perto = etapa in {"sem_registro", "preparacao"} and dias <= 5
        carga_concentrada = carga >= 3 and dias <= 10

        motivos: list[str] = []
        if bloqueado:
            motivos.append(f"material/liberação ainda pendente a {dias} dia(s) da entrega")
        if janela_apertada:
            motivos.append(f"restam {uteis} dia(s) útil(eis), com prazo informado de {prazo} dia(s) úteis")
        if preparacao_perto:
            motivos.append(f"pedido ainda em preparação/sem etapa produtiva a {dias} dia(s) da entrega")
        if carga_concentrada:
            motivos.append(f"{carga} pedidos ainda não Prontos concentram entrega em {entrega.strftime('%d/%m')}")

        if not motivos:
            continue

        # Não vende falsa precisão de capacidade. A severidade representa
        # quantidade/qualidade dos sinais e proximidade do prazo.
        forte = bloqueado or janela_apertada or preparacao_perto
        nivel = "alta" if forte and dias <= 7 else "normal"
        prioridade = 760
        if bloqueado:
            prioridade += 80
        if janela_apertada:
            prioridade += 70
        if preparacao_perto:
            prioridade += 50
        if carga_concentrada:
            prioridade += min(60, (carga - 2) * 20)
        prioridade += max(0, 10 - dias) * 4

        if etapa == "aguardando_liberacao":
            acao = "Confirmar e reservar materiais antes que a janela de produção fique crítica"
        elif etapa == "aguardando_material":
            acao = "Resolver falta de material e validar se o prazo de entrega continua viável"
        elif etapa == "compra_em_andamento":
            acao = "Conferir previsão do fornecedor e proteger a data de entrega"
        elif etapa == "sem_registro":
            acao = "Abrir o Fluxo e definir a etapa de produção enquanto ainda há margem"
        elif etapa == "preparacao":
            acao = "Concluir arte/preparação e liberar a produção antes da janela crítica"
        elif etapa == "pronto_iniciar":
            acao = "Programar o início da produção considerando os demais pedidos da mesma data"
        else:
            acao = "Revisar a sequência de produção e proteger o prazo antes de virar urgência"

        sinais.append({
            "numero_proposta": numero,
            "cliente_nome": str(proposta.get("cliente_nome") or proposta.get("cliente") or "Cliente").strip() or "Cliente",
            "data_entrega": entrega,
            "dias_para_entrega": dias,
            "dias_uteis_restantes": uteis,
            "prazo_producao_dias": prazo,
            "situacao_operacional_chave": etapa,
            "situacao_operacional": etapa_rotulo,
            "carga_mesma_data": carga,
            "nivel": nivel,
            "prioridade": prioridade,
            "motivo": " · ".join(motivos),
            "acao": acao,
            "pressao_janela": True,
        })

    sinais.sort(key=lambda item: (
        0 if item.get("nivel") == "alta" else 1,
        int(item.get("dias_para_entrega") or 999),
        -int(item.get("prioridade") or 0),
        str(item.get("cliente_nome") or "").casefold(),
        str(item.get("numero_proposta") or ""),
    ))
    return sinais[: max(0, int(limite or 0))]
