"""20.4.9-I8.13.5-HF21 — sinais de continuidade do THU.

Serviço puro e somente leitura. Usa as fotografias diárias da Agenda da Anna
para detectar pedidos que permanecem no mesmo estágio/status entre aberturas.
Também permite um sinal no próprio dia quando um prazo hoje/vencido continua no
mesmo estágio desde a fotografia da manhã.

Importante: "sem avanço" aqui significa *sem mudança de status registrada no
Manager*. O serviço não presume que não houve trabalho físico/offline e não
altera proposta, status, contato, produção ou entrega.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable


def _parse_date(valor: Any) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor or "").strip()
    if not texto or texto == "—":
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            candidato = texto[:19] if "T" in texto else texto[:10]
            return datetime.strptime(candidato, fmt).date()
        except (TypeError, ValueError):
            continue
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")).date()
    except (TypeError, ValueError):
        return None


def _fase_status(status: Any) -> str:
    """Normaliza o texto visual da Agenda para um estágio operacional estável.

    Prefixos temporais (ATRASADO, Entrega hoje, Saída hoje) não representam uma
    mudança real de estágio e por isso não quebram a continuidade.
    """
    texto = str(status or "").strip().casefold()
    if not texto:
        return "desconhecido"
    if "entregue" in texto and "aguardando retirada" not in texto:
        return "entregue"
    if "pronto / aguardando retirada ou entrega" in texto or "pronto" in texto:
        return "pronto"
    if "aguardando aprovação" in texto or "aguardando aprovacao" in texto:
        return "aguardando_aprovacao"
    if "aprovado" in texto:
        if "pago" in texto or "mensal" in texto:
            return "aprovado_pago"
        if "pagamento pendente" in texto:
            return "aprovado_pagamento_pendente"
        return "aprovado"
    return "outro"


def _rotulo_fase(fase: str) -> str:
    return {
        "aguardando_aprovacao": "Aguardando aprovação",
        "aprovado_pago": "Aprovado · Pago",
        "aprovado_pagamento_pendente": "Aprovado · Pagamento pendente",
        "aprovado": "Aprovado",
        "pronto": "Pronto / aguardando retirada ou entrega",
    }.get(fase, "Mesmo estágio")


def _linhas_snapshot(snapshot: Any) -> list[dict[str, Any]]:
    if not isinstance(snapshot, dict):
        return []
    linhas = snapshot.get("linhas")
    if not isinstance(linhas, list):
        return []
    return [x for x in linhas if isinstance(x, dict)]


def _historico_por_proposta(
    snapshots: dict[str, Any] | None,
    hoje: date,
) -> dict[str, list[tuple[date, str]]]:
    historico: dict[str, list[tuple[date, str]]] = {}
    if not isinstance(snapshots, dict):
        return historico
    for chave, snapshot in snapshots.items():
        dia = _parse_date(chave)
        if not dia or dia > hoje:
            continue
        for linha in _linhas_snapshot(snapshot):
            numero = str(linha.get("numero_proposta") or "").strip()
            if not numero:
                continue
            historico.setdefault(numero, []).append((dia, _fase_status(linha.get("status"))))
    for numero in list(historico):
        # Se houver mais de uma fotografia acidental no mesmo dia, a última
        # entrada da ordenação é suficiente para o cálculo por dia.
        por_dia: dict[date, str] = {}
        for dia, fase in sorted(historico[numero], key=lambda x: x[0]):
            por_dia[dia] = fase
        historico[numero] = sorted(por_dia.items(), key=lambda x: x[0])
    return historico


def _dias_mesma_fase(registros: list[tuple[date, str]], fase_atual: str, hoje: date) -> tuple[int, date | None]:
    """Retorna dias corridos desde a primeira fotografia consecutiva da fase."""
    iguais = [(d, f) for d, f in registros if d <= hoje]
    if not iguais:
        return 0, None
    inicio: date | None = None
    for dia, fase in reversed(iguais):
        if fase != fase_atual:
            break
        inicio = dia
    if inicio is None:
        return 0, None
    return max(0, (hoje - inicio).days), inicio


def _acao_por_fase(fase: str, dias_entrega: int | None, dias_estagio: int) -> str:
    if fase == "aguardando_aprovacao":
        if dias_entrega is not None and dias_entrega <= 0:
            return "Confirmar com o cliente se o pedido seguirá e ajustar o prazo se necessário"
        return "Revisar o retorno comercial e confirmar se falta decisão do cliente"
    if fase == "aprovado_pagamento_pendente":
        if dias_entrega is not None and dias_entrega <= 1:
            return "Conferir pagamento e, em paralelo, revisar o impacto no prazo operacional"
        return "Conferir pagamento pendente e o próximo marco do pedido"
    if fase in {"aprovado_pago", "aprovado"}:
        if dias_entrega is not None and dias_entrega <= 0:
            return "Revisar o pedido no Fluxo e confirmar o avanço da produção"
        return "Conferir se a produção avançou e registrar o próximo status quando confirmado"
    if fase == "pronto":
        if dias_entrega is not None and dias_entrega <= 0:
            return "Organizar retirada/entrega e concluir a saída quando realmente ocorrer"
        return "Confirmar a programação de retirada/entrega"
    return "Abrir o pedido e conferir o próximo passo"


def montar_sinais_sem_avanco(
    linhas_atuais: Iterable[dict[str, Any]] | None,
    snapshots: dict[str, Any] | None,
    hoje: date,
    *,
    limite: int = 8,
) -> list[dict[str, Any]]:
    """Monta sinais assistidos de pedidos sem mudança de status registrada.

    Um item entra quando:
    - está com entrega hoje/vencida e permanece na mesma fase desde a abertura
      de hoje; ou
    - a mesma fase aparece nas fotografias por 2+ dias corridos.

    Isso mantém o bloco útil no primeiro dia e mais inteligente à medida que o
    histórico de aberturas da Anna cresce.
    """
    historico = _historico_por_proposta(snapshots, hoje)
    hoje_snapshot = {
        numero: any(dia == hoje for dia, _ in regs)
        for numero, regs in historico.items()
    }
    saida: list[dict[str, Any]] = []

    for linha in linhas_atuais or []:
        if not isinstance(linha, dict):
            continue
        numero = str(linha.get("numero_proposta") or "").strip()
        if not numero:
            continue
        fase = _fase_status(linha.get("status"))
        if fase in {"desconhecido", "entregue"}:
            continue
        regs = historico.get(numero, [])
        dias_estagio, desde = _dias_mesma_fase(regs, fase, hoje)
        fase_manha = next((f for d, f in reversed(regs) if d == hoje), None)
        mesma_fase_manha = bool(fase_manha == fase)

        entrega = _parse_date(linha.get("data_entrega") or linha.get("data_entrega_obj"))
        dias_entrega = (entrega - hoje).days if entrega else None

        critico_prazo = dias_entrega is not None and dias_entrega <= 0 and mesma_fase_manha
        recorrente = dias_estagio >= 2
        if not critico_prazo and not recorrente:
            continue

        if dias_entrega is not None and dias_entrega < 0:
            nivel = "urgente"
            prioridade = 1300 + min(abs(dias_entrega), 30) * 10 + min(dias_estagio, 30)
            prazo_txt = f"prazo vencido há {abs(dias_entrega)} dia(s)"
        elif dias_entrega == 0:
            nivel = "urgente"
            prioridade = 1200 + min(dias_estagio, 30)
            prazo_txt = "entrega prevista para hoje"
        elif dias_estagio >= 4:
            nivel = "alta"
            prioridade = 1000 + min(dias_estagio, 30) * 5
            prazo_txt = f"mesmo estágio há {dias_estagio} dia(s)"
        else:
            nivel = "normal"
            prioridade = 800 + min(dias_estagio, 30) * 5
            prazo_txt = f"mesmo estágio há {dias_estagio} dia(s)"

        if dias_estagio > 0:
            continuidade_txt = f"sem mudança de status registrada há {dias_estagio} dia(s)"
        elif hoje_snapshot.get(numero) and mesma_fase_manha:
            continuidade_txt = "sem mudança de status registrada desde a abertura de hoje"
        else:
            continuidade_txt = "sem mudança de status registrada"

        saida.append({
            "numero_proposta": numero,
            "cliente_nome": str(linha.get("cliente_nome") or "Cliente").strip() or "Cliente",
            "telefone": str(linha.get("telefone") or "").strip(),
            "produtos": str(linha.get("produtos") or "—").strip() or "—",
            "status": str(linha.get("status") or "—").strip() or "—",
            "fase": fase,
            "fase_rotulo": _rotulo_fase(fase),
            "data_entrega": str(linha.get("data_entrega") or "—"),
            "dias_para_entrega": dias_entrega,
            "dias_mesma_fase": dias_estagio,
            "desde": desde.isoformat() if desde else "",
            "nivel": nivel,
            "prioridade": prioridade,
            "motivo": f"{prazo_txt} · {continuidade_txt}",
            "acao": _acao_por_fase(fase, dias_entrega, dias_estagio),
        })

    saida.sort(
        key=lambda x: (
            -int(x.get("prioridade") or 0),
            int(x.get("dias_para_entrega")) if x.get("dias_para_entrega") is not None else 99999,
            str(x.get("numero_proposta") or ""),
        )
    )
    return saida[: max(0, int(limite or 0))]
