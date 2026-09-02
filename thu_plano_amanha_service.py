"""20.4.9-I8.13.5-HF26 — plano assistido do próximo dia para o THU.

Somente leitura. O plano não cria capacidade fictícia, não muda status e não
registra ações. Ele reaproveita os sinais preventivos homologados da HF25 e
acrescenta saídas já Prontas com entrega prevista para amanhã.

Urgências que já pertencem a hoje (atrasos e pedidos ainda não Prontos com
entrega amanhã) não são repetidas aqui: continuam na Agenda Executiva como
"Fazer agora".
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Iterable

from proposal_status import resumo_status


_MATERIAL = {"aguardando_liberacao", "aguardando_material", "compra_em_andamento"}


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


def _numero(item: dict[str, Any]) -> str:
    return str(item.get("numero_proposta") or "").strip()


def montar_plano_amanha(
    propostas: Iterable[dict] | None,
    hoje: date,
    *,
    sinais_prevencao: Iterable[dict] | None = None,
    limite: int = 10,
) -> list[dict[str, Any]]:
    """Monta ações assistidas para o próximo dia civil.

    Regras:
    - sinais preventivos da HF25 viram preparação de Produção/Materiais;
    - pedidos já Prontos com entrega amanhã viram preparação de Saída;
    - pedido não Pronto com entrega amanhã não entra, pois já é urgência de hoje;
    - atrasados não entram, pois continuam em ``Fazer agora``;
    - uma proposta aparece no máximo uma vez.
    """
    hoje = hoje or date.today()
    amanha = hoje + timedelta(days=1)
    por_numero: dict[str, dict[str, Any]] = {}

    # Base preventiva já homologada na HF25. Todos estes sinais representam
    # risco futuro, não atraso atual; são portanto bons candidatos para a
    # preparação do próximo dia.
    for sinal in sinais_prevencao or []:
        if not isinstance(sinal, dict):
            continue
        numero = _numero(sinal)
        entrega = _data(sinal.get("data_entrega"))
        if not numero or entrega is None or entrega <= hoje:
            continue
        etapa = str(sinal.get("situacao_operacional_chave") or "").strip()
        dominio = "Materiais" if etapa in _MATERIAL else "Produção"
        icone = "📦" if dominio == "Materiais" else "🏭"
        nivel = str(sinal.get("nivel") or "normal").strip().casefold()
        score = int(sinal.get("prioridade") or 0) + (120 if dominio == "Materiais" else 80)
        if nivel == "alta":
            score += 50
        por_numero[numero] = {
            "numero_proposta": numero,
            "cliente_nome": str(sinal.get("cliente_nome") or "Cliente").strip() or "Cliente",
            "data_entrega": entrega,
            "dias_para_entrega": int(sinal.get("dias_para_entrega") or max(0, (entrega - hoje).days)),
            "dominio": dominio,
            "icone": icone,
            "motivo": str(sinal.get("motivo") or "Sinal preventivo de prazo").strip(),
            "acao": str(sinal.get("acao") or "Revisar sequência e proteger o prazo").strip(),
            "prioridade": score,
            "origem": "prevencao_prazo",
        }

    # Saídas de amanhã: só entram quando o pedido já está Pronto. Se ainda não
    # está Pronto, a situação é crítica hoje e deve permanecer na agenda atual,
    # não ser adiada para este plano.
    for proposta in propostas or []:
        if not isinstance(proposta, dict):
            continue
        estado = resumo_status(proposta)
        if not estado.get("ativa") or estado.get("entregue") or not estado.get("pronto"):
            continue
        entrega = _data(proposta.get("data_entrega"))
        if entrega != amanha:
            continue
        numero = _numero(proposta)
        if not numero:
            continue
        cliente = str(proposta.get("cliente_nome") or proposta.get("cliente") or "Cliente").strip() or "Cliente"
        candidato = {
            "numero_proposta": numero,
            "cliente_nome": cliente,
            "data_entrega": entrega,
            "dias_para_entrega": 1,
            "dominio": "Saída",
            "icone": "🚚",
            "motivo": "Pedido já está Pronto e tem retirada/entrega prevista para amanhã",
            "acao": "Confirmar cliente e deixar retirada/entrega organizada no início do dia",
            "prioridade": 1100,
            "origem": "saida_amanha",
        }
        atual = por_numero.get(numero)
        if atual is None or int(candidato["prioridade"]) > int(atual.get("prioridade") or 0):
            por_numero[numero] = candidato

    saida = list(por_numero.values())
    ordem = {"Saída": 0, "Materiais": 1, "Produção": 2}
    saida.sort(key=lambda item: (
        -int(item.get("prioridade") or 0),
        ordem.get(str(item.get("dominio") or ""), 9),
        item.get("data_entrega") or date.max,
        str(item.get("cliente_nome") or "").casefold(),
        str(item.get("numero_proposta") or ""),
    ))
    return saida[: max(0, int(limite or 0))]


def resumo_plano_amanha(plano: Iterable[dict] | None) -> dict[str, int]:
    itens = [x for x in (plano or []) if isinstance(x, dict)]
    return {
        "total": len(itens),
        "producao": sum(1 for x in itens if x.get("dominio") == "Produção"),
        "materiais": sum(1 for x in itens if x.get("dominio") == "Materiais"),
        "saidas": sum(1 for x in itens if x.get("dominio") == "Saída"),
    }
