"""20.4.9-I8.13.1 — Inteligência de Prioridades e Atrasos.

Motor somente leitura. Não cria status, não grava prioridade e não altera bancos.
A prioridade é derivada em tempo real da proposta oficial, do prazo, da leitura
de produção/material da I8.12.8 e da fila de saída da I8.13.

Regra essencial: pedido oficialmente Pronto nunca é atraso de produção. Quando o
prazo previsto passa, a urgência muda de domínio e vira ``saída atrasada``.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable

from proposal_status import resumo_status


_MATERIAL_BLOQUEADO = {"aguardando_liberacao", "aguardando_material", "compra_em_andamento"}


def _data(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _texto(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _indexar(linhas: Iterable[dict] | None) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for linha in linhas or []:
        if not isinstance(linha, dict):
            continue
        numero = _texto(linha.get("numero_proposta"))
        if numero:
            out[numero] = linha
    return out


def _acao_producao(linha_producao: dict | None) -> str:
    linha = linha_producao or {}
    chave = _texto(linha.get("situacao_operacional_chave"))
    if chave == "aguardando_liberacao":
        return "Confirmar e reservar materiais"
    if chave == "aguardando_material":
        return "Resolver falta de material"
    if chave == "compra_em_andamento":
        return "Acompanhar recebimento do fornecedor"
    return _texto(linha.get("proxima_acao_producao"), "Revisar pedido no Fluxo")


def _classificar_nao_pronto(
    *,
    dias: int | None,
    risco: bool,
) -> tuple[str, str, int, str]:
    """Retorna (chave, rótulo, rank, motivo_base). Menor rank = maior urgência."""
    if dias is not None and dias < 0:
        n = abs(dias)
        return "atrasado_producao", "🚨 ATRASADO", 0, f"Prazo vencido há {n} dia(s) e produção ainda não concluída"
    if dias == 0:
        return "vence_hoje", "🔴 VENCE HOJE", 1, "Entrega prevista para hoje e pedido ainda não está Pronto"
    if risco:
        return "risco_atraso", "🔴 RISCO DE ATRASO", 1, "Produção/material indica risco para o prazo informado"
    if dias is not None and 1 <= dias <= 2:
        return "proximo_prazo", "🟠 PRÓXIMO DO PRAZO", 2, f"Faltam {dias} dia(s) para a entrega"
    if dias is not None and 3 <= dias <= 5:
        return "atencao_prazo", "🟡 ATENÇÃO AO PRAZO", 3, f"Faltam {dias} dia(s) para a entrega"
    if dias is None:
        return "sem_data", "⚪ SEM DATA", 4, "Pedido aprovado sem data de entrega registrada"
    return "dentro_prazo", "🟢 DENTRO DO PRAZO", 5, f"Faltam {dias} dia(s) para a entrega"


def _classificar_pronto(
    *,
    dias: int | None,
    dias_aguardando: int | None,
    avisado: bool,
) -> tuple[str, str, int, str]:
    """Prioridade de saída. Nunca devolve categoria de atraso de produção."""
    if dias is not None and dias < 0:
        n = abs(dias)
        return "saida_atrasada", "🚚 SAÍDA ATRASADA", 0, f"Pedido está Pronto, mas a entrega prevista venceu há {n} dia(s)"
    if dias == 0:
        return "saida_hoje", "📦 SAÍDA HOJE", 1, "Pedido está Pronto e a saída está prevista para hoje"
    if not avisado:
        return "cliente_nao_avisado", "📱 CLIENTE NÃO AVISADO", 2, "Pedido está Pronto e ainda não há registro de aviso ao cliente"
    if isinstance(dias_aguardando, int) and dias_aguardando >= 3:
        return "pronto_3_dias", "⏳ PRONTO 3+ DIAS", 2, f"Pedido aguarda saída há {dias_aguardando} dia(s)"
    return "pronto_aguardando", "📦 AGUARDANDO SAÍDA", 4, "Produção concluída; aguardando retirada ou entrega"


def montar_prioridades_operacionais(
    propostas: Iterable[dict],
    hoje: date,
    *,
    central_producao: Iterable[dict] | None = None,
    fila_entregas: Iterable[dict] | None = None,
    resumo_produtos=None,
) -> list[dict]:
    """Monta uma fila única e calculada de pedidos aprovados ainda abertos.

    ``central_producao`` e ``fila_entregas`` são leituras derivadas opcionais.
    A proposta oficial continua sendo a fonte dos marcos Aprovado/Pronto/Entregue.
    """
    producao_por_numero = _indexar(central_producao)
    entrega_por_numero = _indexar(fila_entregas)
    linhas: list[dict] = []

    for proposta in propostas or []:
        if not isinstance(proposta, dict):
            continue
        status = resumo_status(proposta)
        if not status.get("aprovado") or not status.get("ativa") or status.get("entregue"):
            continue

        numero = _texto(proposta.get("numero_proposta"))
        if not numero:
            continue
        cliente = _texto(proposta.get("cliente_nome") or proposta.get("cliente"), "Cliente")
        data_entrega = _data(proposta.get("data_entrega"))
        dias = (data_entrega - hoje).days if data_entrega is not None else None
        prod = producao_por_numero.get(numero, {})
        saida = entrega_por_numero.get(numero, {})
        pronto = bool(status.get("pronto"))
        risco = bool(prod.get("risco_atraso"))
        situacao_chave = _texto(prod.get("situacao_operacional_chave"))
        bloqueado_material = situacao_chave in _MATERIAL_BLOQUEADO

        if pronto:
            dias_aguardando = saida.get("dias_aguardando")
            avisado = bool(saida.get("cliente_avisado"))
            chave, rotulo, rank, motivo = _classificar_pronto(
                dias=dias,
                dias_aguardando=dias_aguardando if isinstance(dias_aguardando, int) else None,
                avisado=avisado,
            )
            if not avisado:
                acao = "Avisar cliente e organizar retirada/entrega"
            else:
                acao = "Concluir retirada/entrega"
            area = "Entrega"
        else:
            dias_aguardando = None
            avisado = False
            chave, rotulo, rank, motivo = _classificar_nao_pronto(dias=dias, risco=risco)
            acao = _acao_producao(prod)
            area = "Produção"

        # Material bloqueado não cria uma categoria paralela: ele explica a
        # urgência e direciona a ação dentro da mesma janela de prazo.
        motivo_detalhe = motivo
        if not pronto and bloqueado_material:
            situacao = _texto(prod.get("situacao_operacional"), "Material pendente")
            motivo_detalhe = f"{motivo} · {situacao}"

        resumo = resumo_produtos(proposta) if callable(resumo_produtos) else _texto(prod.get("resumo_produtos"))
        linhas.append({
            "numero_proposta": numero,
            "cliente_nome": cliente,
            "resumo_produtos": resumo,
            "data_entrega": data_entrega,
            "dias_ate_entrega": dias,
            "pronto": pronto,
            "pago": bool(status.get("pago")),
            "area": area,
            "prioridade_chave": chave,
            "prioridade_rotulo": rotulo,
            "prioridade_rank": rank,
            "motivo_prioridade": motivo_detalhe,
            "proxima_acao": acao,
            "risco_atraso": risco if not pronto else False,
            "bloqueado_material": bloqueado_material if not pronto else False,
            "situacao_operacional": _texto(prod.get("situacao_operacional")),
            "situacao_operacional_chave": situacao_chave,
            "cliente_avisado": avisado,
            "dias_aguardando_pronto": dias_aguardando,
            "proposta": proposta,
        })

    # Menor rank primeiro. Dentro do mesmo nível, prazo vencido/mais próximo
    # domina; depois pedidos prontos ainda não avisados; por fim identificação.
    def _sort(linha: dict):
        dias = linha.get("dias_ate_entrega")
        prazo_sort = dias if isinstance(dias, int) else 999999
        return (
            int(linha.get("prioridade_rank", 9)),
            prazo_sort,
            0 if linha.get("pronto") and not linha.get("cliente_avisado") else 1,
            str(linha.get("cliente_nome") or "").casefold(),
            str(linha.get("numero_proposta") or ""),
        )

    return sorted(linhas, key=_sort)


def resumo_prioridades(linhas: Iterable[dict]) -> dict[str, int]:
    itens = [x for x in (linhas or []) if isinstance(x, dict)]
    return {
        "total": len(itens),
        "criticos": sum(1 for x in itens if int(x.get("prioridade_rank", 9)) == 0),
        "vence_hoje": sum(1 for x in itens if x.get("prioridade_chave") in {"vence_hoje", "saida_hoje"}),
        "proximos_2_dias": sum(1 for x in itens if x.get("prioridade_chave") == "proximo_prazo"),
        "prontos_saida": sum(1 for x in itens if x.get("pronto")),
        "sem_data": sum(1 for x in itens if x.get("prioridade_chave") == "sem_data"),
        "atrasados_producao": sum(1 for x in itens if x.get("prioridade_chave") == "atrasado_producao"),
        "saidas_atrasadas": sum(1 for x in itens if x.get("prioridade_chave") == "saida_atrasada"),
        "nao_avisados": sum(1 for x in itens if x.get("prioridade_chave") == "cliente_nao_avisado"),
    }


def indexar_prioridades(linhas: Iterable[dict]) -> dict[str, dict]:
    return _indexar(linhas)
