"""Painel Alpha Intelligence.

Análises determinísticas sobre os dados reais do FestManager. Não envia dados
para serviços externos e não altera registros operacionais.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, date
import re
import unicodedata

import pandas as pd
import streamlit as st


def _txt(value):
    return str(value or "").strip()


def _norm(value):
    text = unicodedata.normalize("NFKD", _txt(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", text).strip().upper()


def _money(value):
    if isinstance(value, (int, float)):
        return float(value)
    text = _txt(value).replace("R$", "").replace(" ", "")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except Exception:
        return 0.0


def _date(value):
    text = _txt(value)
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(text[:16], fmt).date()
        except Exception:
            pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except Exception:
        return None


def _proposal_customer_key(prop):
    return _txt(prop.get("relacionamento_id") or prop.get("cliente_id") or prop.get("customer_id")) or _norm(
        prop.get("cliente_nome") or prop.get("cliente") or prop.get("nome_cliente")
    )


def _customer_key(cli):
    return _txt(cli.get("relacionamento_id") or cli.get("id") or cli.get("cliente_id")) or _norm(
        cli.get("nome") or cli.get("Nome") or cli.get("cliente_nome")
    )


def _customer_name(cli):
    return _txt(cli.get("nome") or cli.get("Nome") or cli.get("cliente_nome")) or "Sem nome"


def _item_name(item):
    return _txt(item.get("produto") or item.get("nome") or item.get("Nome") or item.get("descricao")) or "Produto não informado"


def build_intelligence(clientes, historico, catalogo, producao, today=None):
    today = today or date.today()
    clientes = clientes if isinstance(clientes, list) else []
    historico = historico if isinstance(historico, list) else []
    catalogo = catalogo if isinstance(catalogo, list) else []
    producao = producao if isinstance(producao, list) else []

    customer_map = {_customer_key(c): c for c in clientes if _customer_key(c)}
    by_customer = defaultdict(list)
    product_counter = Counter()
    product_revenue = Counter()
    pairs = Counter()
    monthly = Counter()

    for prop in historico:
        key = _proposal_customer_key(prop)
        if key:
            by_customer[key].append(prop)
        items = prop.get("itens") or []
        names = []
        for item in items:
            name = _item_name(item)
            qty = max(1.0, _money(item.get("quantidade") or 1))
            unit = _money(item.get("valor_unitario") or item.get("preco") or 0)
            product_counter[name] += qty
            product_revenue[name] += qty * unit
            names.append(name)
        unique = sorted(set(names))
        for i, first in enumerate(unique):
            for second in unique[i + 1:]:
                pairs[(first, second)] += 1
        d = _date(prop.get("data_geracao") or prop.get("data") or prop.get("criado_em"))
        if d:
            monthly[f"{d.year:04d}-{d.month:02d}"] += _money(prop.get("valor_total"))

    profiles = []
    all_keys = set(customer_map) | set(by_customer)
    for key in all_keys:
        cli = customer_map.get(key, {})
        props = by_customer.get(key, [])
        values = [_money(p.get("valor_total")) for p in props]
        total = sum(values)
        dates = [d for d in (_date(p.get("data_geracao") or p.get("data") or p.get("criado_em")) for p in props) if d]
        last = max(dates) if dates else None
        days = (today - last).days if last else None
        own_products = Counter()
        for p in props:
            for item in p.get("itens") or []:
                own_products[_item_name(item)] += max(1.0, _money(item.get("quantidade") or 1))
        favorite = [name for name, _ in own_products.most_common(5)]
        if not props:
            status = "Sem compras"
            score = 15
        else:
            recency_points = 35 if days is not None and days <= 30 else 25 if days is not None and days <= 90 else 10 if days is not None and days <= 180 else 0
            freq_points = min(30, len(props) * 8)
            value_points = min(25, int(total / 100))
            score = min(100, 10 + recency_points + freq_points + value_points)
            status = "Ativo" if days is not None and days <= 90 else "Atenção" if days is not None and days <= 180 else "Recuperar"
        level = "Diamante" if score >= 90 else "Ouro" if score >= 75 else "Prata" if score >= 55 else "Bronze"
        profiles.append({
            "key": key,
            "nome": _customer_name(cli) if cli else _txt(props[0].get("cliente_nome")) if props else key,
            "propostas": len(props),
            "total": total,
            "ticket": total / len(props) if props else 0,
            "ultima_compra": last.isoformat() if last else "",
            "dias_sem_compra": days,
            "status": status,
            "score": score,
            "nivel": level,
            "favoritos": favorite,
        })
    profiles.sort(key=lambda x: (-x["score"], -x["total"], x["nome"]))

    top_products = [{"produto": p, "quantidade": q, "receita": product_revenue[p]} for p, q in product_counter.most_common(20)]
    combos = [{"produto_a": a, "produto_b": b, "vezes_juntos": n} for (a, b), n in pairs.most_common(20)]

    catalog_names = [_txt(p.get("Nome") or p.get("nome")) for p in catalogo]
    cross_sell = []
    for profile in profiles:
        bought = set(profile["favoritos"])
        suggestions = []
        for combo in combos:
            if combo["produto_a"] in bought and combo["produto_b"] not in bought:
                suggestions.append((combo["produto_b"], combo["vezes_juntos"]))
            elif combo["produto_b"] in bought and combo["produto_a"] not in bought:
                suggestions.append((combo["produto_a"], combo["vezes_juntos"]))
        seen = set()
        clean = []
        for product, strength in sorted(suggestions, key=lambda x: -x[1]):
            if product not in seen:
                seen.add(product)
                clean.append(product)
        if not clean and catalog_names and bought:
            clean = [p for p in catalog_names if p and p not in bought][:3]
        if clean:
            cross_sell.append({"cliente": profile["nome"], "sugestoes": clean[:3], "score": profile["score"]})

    production_open = [x for x in producao if _norm(x.get("status")) not in {"ENTREGUE", "FINALIZADO", "ARQUIVADO"}]
    total_revenue = sum(_money(p.get("valor_total")) for p in historico)
    return {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "resumo": {
            "clientes": len(profiles), "propostas": len(historico), "receita": total_revenue,
            "ticket_medio": total_revenue / len(historico) if historico else 0,
            "producao_aberta": len(production_open),
        },
        "clientes": profiles,
        "produtos": top_products,
        "combinacoes": combos,
        "venda_cruzada": cross_sell,
        "mensal": [{"mes": k, "receita": v} for k, v in sorted(monthly.items())],
    }


def render_alpha_intelligence(clientes, historico, catalogo, producao, save_snapshot=None, today=None):
    st.header("🧠 Alpha Intelligence")
    st.caption("Conhecimento comercial calculado a partir dos dados reais da Alphafest. Nenhuma resposta ou publicação é enviada automaticamente.")
    data = build_intelligence(clientes, historico, catalogo, producao, today=today)
    summary = data["resumo"]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Relacionamentos analisados", summary["clientes"])
    c2.metric("Propostas", summary["propostas"])
    c3.metric("Receita histórica", f"R$ {summary['receita']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c4.metric("Ticket médio", f"R$ {summary['ticket_medio']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c5.metric("Produção em aberto", summary["producao_aberta"])

    if save_snapshot is not None:
        if st.button("🔄 Recalcular e salvar conhecimento", type="primary", use_container_width=True):
            save_snapshot(data)
            st.success("Conhecimento recalculado e salvo sem alterar os dados operacionais.")

    tab_action, tab_customer, tab_products, tab_trends = st.tabs([
        "🎯 Fazer agora", "👤 Memória do relacionamento", "📦 Produtos e combinações", "📈 Tendências"
    ])

    with tab_action:
        left, right = st.columns(2)
        with left:
            st.subheader("Clientes para recuperar")
            recover = [p for p in data["clientes"] if p["status"] == "Recuperar"][:15]
            if not recover:
                st.info("Nenhum cliente com histórico antigo suficiente para recuperação.")
            for p in recover:
                with st.container(border=True):
                    st.markdown(f"**{p['nome']}** · {p['nivel']} · {p['score']}/100")
                    st.caption(f"{p['propostas']} proposta(s) · Ticket R$ {p['ticket']:.2f} · {p['dias_sem_compra']} dias sem comprar")
                    if p["favoritos"]:
                        st.write("Retomar com: " + ", ".join(p["favoritos"][:3]))
        with right:
            st.subheader("Venda cruzada sugerida")
            if not data["venda_cruzada"]:
                st.info("Ainda não há histórico suficiente para aprender combinações confiáveis.")
            for item in data["venda_cruzada"][:15]:
                with st.container(border=True):
                    st.markdown(f"**{item['cliente']}**")
                    st.write("Oferecer: " + " · ".join(item["sugestoes"]))

    with tab_customer:
        profiles = data["clientes"]
        if not profiles:
            st.info("Cadastre clientes e propostas para formar a memória comercial.")
        else:
            names = [f"{p['nome']} — {p['score']}/100" for p in profiles]
            selected = st.selectbox("Relacionamento", names)
            p = profiles[names.index(selected)]
            a, b, c, d = st.columns(4)
            a.metric("Índice Alpha", f"{p['score']}/100")
            b.metric("Nível", p["nivel"])
            c.metric("Propostas", p["propostas"])
            d.metric("Ticket médio", f"R$ {p['ticket']:.2f}")
            st.markdown(f"**Situação comercial:** {p['status']}")
            st.write("**Produtos preferidos:** " + (", ".join(p["favoritos"]) if p["favoritos"] else "Ainda não identificados"))
            if p["ultima_compra"]:
                st.caption(f"Última compra: {p['ultima_compra']} · {p['dias_sem_compra']} dias")

    with tab_products:
        products = pd.DataFrame(data["produtos"])
        if products.empty:
            st.info("Ainda não existem itens suficientes no histórico.")
        else:
            st.subheader("Produtos mais vendidos")
            st.dataframe(products.head(20), use_container_width=True, hide_index=True)
        combos = pd.DataFrame(data["combinacoes"])
        if not combos.empty:
            st.subheader("Produtos comprados juntos")
            st.dataframe(combos.head(20), use_container_width=True, hide_index=True)

    with tab_trends:
        monthly = pd.DataFrame(data["mensal"])
        if monthly.empty:
            st.info("Ainda não existem datas suficientes para montar a tendência.")
        else:
            st.subheader("Receita por mês")
            st.line_chart(monthly.set_index("mes")["receita"])
            st.dataframe(monthly, use_container_width=True, hide_index=True)

    st.caption(f"Último cálculo nesta tela: {data['gerado_em']}")
    return data
