"""Inteligência de clientes do AlphaFest Center Innovation.

Módulo somente leitura: transforma dados já existentes em indicadores para o
perfil de gestão sem alterar a operação da Anna nem gravar documentos.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from typing import Any, Callable, Dict, Iterable, List, Mapping, Sequence

import streamlit as st


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _data(valor: Any) -> date | None:
    texto = _texto(valor)
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(texto[:26], formato).date()
        except (TypeError, ValueError):
            continue
    return None


def _moeda(valor: float) -> str:
    return f"R$ {float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _nome_cliente(cliente: Mapping[str, Any]) -> str:
    return _texto(cliente.get("nome")) or "Cliente sem nome"


def _status_financeiro(cliente: Mapping[str, Any]) -> tuple[str, str]:
    politica = cliente.get("politica_atendimento", {}) or {}
    nivel = _texto(politica.get("nivel")) or "Normal"
    classificacao = _texto(cliente.get("classificacao_relacionamento")) or "Não classificado"
    if bool(politica.get("exigir_pagamento_antecipado")):
        return "🔴 Pagamento antecipado", "Produzir somente após confirmação integral."
    if nivel == "Bloqueado" or classificacao == "Bloqueado":
        return "⚫ Restrição comercial", "Atendimento depende de autorização da gestão."
    if nivel in {"Atenção", "Monitorado"} or classificacao in {"Atenção", "Restrito"}:
        return "🟤 Financeiro sensível", "Revisar histórico e considerar sinal antes da produção."
    return "🟢 Regular", "Sem restrição financeira manual registrada."


def _produto_nome(item: Mapping[str, Any]) -> str:
    return _texto(item.get("produto") or item.get("nome") or item.get("descricao"))


def _calcular_perfil(
    cliente: Mapping[str, Any],
    propostas: Sequence[Mapping[str, Any]],
    calcular_total: Callable[[Mapping[str, Any]], float],
    hoje: date,
) -> Dict[str, Any]:
    quantidade = len(propostas)
    aprovadas = [p for p in propostas if bool(p.get("aprovado"))]
    pagas = [p for p in propostas if bool(p.get("pago"))]
    entregues = [p for p in propostas if bool(p.get("entregue"))]
    aguardando = [p for p in propostas if not bool(p.get("aprovado")) and not bool(p.get("encerrado"))]
    encerradas = [p for p in propostas if bool(p.get("encerrado"))]

    total_orcado = sum(calcular_total(p) for p in propostas)
    total_aprovado = sum(calcular_total(p) for p in aprovadas)
    total_pago = sum(calcular_total(p) for p in pagas)
    ticket = total_aprovado / len(aprovadas) if aprovadas else (total_orcado / quantidade if quantidade else 0.0)
    conversao = (len(aprovadas) / quantidade * 100.0) if quantidade else 0.0

    datas = [_data(p.get("data_geracao")) for p in propostas]
    datas_validas = [d for d in datas if d]
    primeira = min(datas_validas) if datas_validas else None
    ultima = max(datas_validas) if datas_validas else None
    dias_sem_compra = (hoje - ultima).days if ultima else None

    produtos = Counter()
    for proposta in propostas:
        for item in proposta.get("itens", []) or []:
            nome = _produto_nome(item)
            if nome:
                produtos[nome] += int(item.get("quantidade", 1) or 1)

    # AlphaScore operacional (0–100), transparente e determinístico.
    pontos_frequencia = min(25.0, quantidade * 3.0)
    pontos_conversao = min(25.0, conversao * 0.25)
    pontos_pagamento = min(20.0, (len(pagas) / len(aprovadas) * 20.0) if aprovadas else 0.0)
    pontos_entrega = min(15.0, (len(entregues) / len(aprovadas) * 15.0) if aprovadas else 0.0)
    if dias_sem_compra is None:
        pontos_recencia = 0.0
    elif dias_sem_compra <= 30:
        pontos_recencia = 15.0
    elif dias_sem_compra <= 90:
        pontos_recencia = 10.0
    elif dias_sem_compra <= 180:
        pontos_recencia = 5.0
    else:
        pontos_recencia = 1.0
    score = round(min(100.0, pontos_frequencia + pontos_conversao + pontos_pagamento + pontos_entrega + pontos_recencia))

    if score >= 80:
        faixa = "💎 Cliente Ouro"
    elif score >= 60:
        faixa = "⭐ Cliente Frequente"
    elif score >= 35:
        faixa = "🟢 Cliente em desenvolvimento"
    elif quantidade:
        faixa = "🌱 Cliente novo/ocasional"
    else:
        faixa = "⚪ Sem histórico comercial"

    financeiro, orientacao_financeira = _status_financeiro(cliente)
    recomendacoes: List[str] = []
    if aguardando:
        recomendacoes.append(f"Acompanhar {len(aguardando)} orçamento(s) aguardando aprovação.")
    if dias_sem_compra is not None and dias_sem_compra > 120 and aprovadas:
        recomendacoes.append(f"Cliente está há {dias_sem_compra} dias sem nova compra; considerar contato de recuperação.")
    if produtos:
        recomendacoes.append(f"Produto mais recorrente: {produtos.most_common(1)[0][0]}.")
    if financeiro.startswith(("🔴", "⚫", "🟤")):
        recomendacoes.append(orientacao_financeira)
    if not recomendacoes:
        recomendacoes.append("Manter relacionamento e registrar o próximo contato comercial.")

    return {
        "cliente": cliente,
        "quantidade": quantidade,
        "aprovadas": len(aprovadas),
        "pagas": len(pagas),
        "entregues": len(entregues),
        "aguardando": len(aguardando),
        "encerradas": len(encerradas),
        "total_orcado": total_orcado,
        "total_aprovado": total_aprovado,
        "total_pago": total_pago,
        "ticket": ticket,
        "conversao": conversao,
        "primeira": primeira,
        "ultima": ultima,
        "dias_sem_compra": dias_sem_compra,
        "produtos": produtos.most_common(5),
        "score": score,
        "faixa": faixa,
        "financeiro": financeiro,
        "orientacao_financeira": orientacao_financeira,
        "recomendacoes": recomendacoes,
        "propostas": list(propostas),
    }


def renderizar_inteligencia_clientes(
    clientes: Sequence[Mapping[str, Any]],
    propostas_por_cliente: Callable[[Mapping[str, Any]], Sequence[Mapping[str, Any]]],
    calcular_total: Callable[[Mapping[str, Any]], float],
    hoje: date,
) -> None:
    """Renderiza o módulo gerencial sem realizar qualquer gravação."""
    st.header("🧠 Inteligência dos Clientes")
    st.caption("AlphaFest Center Innovation · leitura gerencial dos dados alimentados pela operação. Este módulo não altera cadastros nem propostas.")

    perfis = [
        _calcular_perfil(cliente, propostas_por_cliente(cliente), calcular_total, hoje)
        for cliente in clientes
        if "Cliente" in (cliente.get("papeis") or ["Cliente"])
    ]
    perfis.sort(key=lambda p: (p["score"], p["total_aprovado"]), reverse=True)

    total_clientes = len(perfis)
    com_historico = sum(1 for p in perfis if p["quantidade"])
    vip_ouro = sum(1 for p in perfis if p["score"] >= 80)
    aguardando_total = sum(p["aguardando"] for p in perfis)
    receita_confirmada = sum(p["total_pago"] for p in perfis)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Clientes", total_clientes)
    c2.metric("Com histórico", com_historico)
    c3.metric("Ouro (score ≥ 80)", vip_ouro)
    c4.metric("Orçamentos aguardando", aguardando_total)
    c5.metric("Recebido registrado", _moeda(receita_confirmada))

    termo = st.text_input(
        "Pesquisar cliente",
        placeholder="Nome, telefone, cidade, classificação ou produto",
        key="aci_clientes_busca",
    ).strip().casefold()
    faixa = st.selectbox(
        "Filtrar perfil",
        ["Todos", "Cliente Ouro", "Cliente Frequente", "Em desenvolvimento", "Novo/ocasional", "Sem histórico"],
        key="aci_clientes_faixa",
    )

    def atende(perfil: Mapping[str, Any]) -> bool:
        cliente = perfil["cliente"]
        base = " ".join([
            _nome_cliente(cliente), _texto(cliente.get("whatsapp")), _texto(cliente.get("cidade")),
            _texto(cliente.get("classificacao_relacionamento")),
            " ".join(nome for nome, _ in perfil["produtos"]), perfil["faixa"], perfil["financeiro"],
        ]).casefold()
        if termo and termo not in base:
            return False
        mapa = {
            "Cliente Ouro": perfil["score"] >= 80,
            "Cliente Frequente": 60 <= perfil["score"] < 80,
            "Em desenvolvimento": 35 <= perfil["score"] < 60,
            "Novo/ocasional": 0 < perfil["score"] < 35 and perfil["quantidade"] > 0,
            "Sem histórico": perfil["quantidade"] == 0,
        }
        return faixa == "Todos" or mapa.get(faixa, True)

    filtrados = [p for p in perfis if atende(p)]
    st.write(f"**{len(filtrados)} cliente(s) encontrado(s)**")
    if not filtrados:
        st.info("Nenhum cliente corresponde aos filtros selecionados.")
        return

    opcoes = {f"{_nome_cliente(p['cliente'])} · Score {p['score']} · {p['quantidade']} proposta(s)": p for p in filtrados}
    escolha = st.selectbox("Abrir ficha inteligente", list(opcoes.keys()), key="aci_cliente_selecionado")
    perfil = opcoes[escolha]
    cliente = perfil["cliente"]

    st.divider()
    topo1, topo2 = st.columns([2, 1])
    with topo1:
        st.subheader(_nome_cliente(cliente))
        st.write(f"**{perfil['faixa']}**")
        st.caption(" · ".join(filter(None, [
            _texto(cliente.get("whatsapp")), _texto(cliente.get("cidade")),
            _texto(cliente.get("classificacao_relacionamento")),
        ])) or "Cadastro sem contatos complementares")
    with topo2:
        st.metric("AlphaScore operacional", f"{perfil['score']}/100")
        st.progress(perfil["score"] / 100.0)
        st.caption("Pontuação baseada em frequência, conversão, pagamento, entrega e recência.")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Propostas", perfil["quantidade"])
    m2.metric("Aprovadas", perfil["aprovadas"], f"{perfil['conversao']:.1f}% conversão")
    m3.metric("Total aprovado", _moeda(perfil["total_aprovado"]))
    m4.metric("Ticket médio", _moeda(perfil["ticket"]))

    detalhe1, detalhe2 = st.columns(2)
    with detalhe1:
        st.markdown("#### 💰 Perfil financeiro")
        st.write(f"**{perfil['financeiro']}**")
        st.caption(perfil["orientacao_financeira"])
        st.write(f"**Pago registrado:** {_moeda(perfil['total_pago'])}")
        st.write(f"**Pagas:** {perfil['pagas']} · **Entregues:** {perfil['entregues']}")
        st.write(f"**Aguardando aprovação:** {perfil['aguardando']} · **Encerradas:** {perfil['encerradas']}")
        if perfil["ultima"]:
            st.write(f"**Último orçamento:** {perfil['ultima'].strftime('%d/%m/%Y')}")
            st.write(f"**Dias desde o último registro:** {perfil['dias_sem_compra']}")
    with detalhe2:
        st.markdown("#### 📦 Perfil de compra")
        if perfil["produtos"]:
            for nome, quantidade in perfil["produtos"]:
                st.write(f"• **{nome}** — {quantidade} unidade(s)/registro(s)")
        else:
            st.info("Ainda não há itens suficientes para identificar preferências.")
        st.markdown("#### 💡 Recomendações do THU")
        for recomendacao in perfil["recomendacoes"]:
            st.write(f"• {recomendacao}")

    with st.expander("📋 Histórico comercial resumido", expanded=False):
        propostas = sorted(
            perfil["propostas"],
            key=lambda p: _data(p.get("data_geracao")) or date.min,
            reverse=True,
        )
        if not propostas:
            st.info("Cliente ainda não possui propostas vinculadas.")
        for proposta in propostas[:50]:
            status = "Entregue" if proposta.get("entregue") else "Pago" if proposta.get("pago") else "Aprovado" if proposta.get("aprovado") else "Encerrado" if proposta.get("encerrado") else "Aguardando"
            st.write(
                f"**{_texto(proposta.get('numero_proposta')) or 'Sem número'}** · "
                f"{_texto(proposta.get('data_geracao')) or 'Sem data'} · "
                f"{_moeda(calcular_total(proposta))} · {status}"
            )
