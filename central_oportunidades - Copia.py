"""Central de Oportunidades da Alphafest.

Módulo isolado: qualquer falha aqui não impede o atendimento operacional.
Ele trabalha sobre o mesmo documento de atendimentos, sem migração destrutiva.
"""
from __future__ import annotations

import re
import urllib.parse
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List

import pandas as pd
import streamlit as st

CANAIS_CAPTACAO = ["Instagram", "Facebook", "TikTok", "YouTube", "Site / Catálogo", "Google", "Indicação", "Loja física", "Outro"]
TIPOS_CONTEUDO = ["Reel", "Story", "Post", "Comentário", "Short", "Vídeo", "Página do site", "Catálogo", "Anúncio", "Pesquisa Google", "Indicação", "Outro"]
MOTIVOS_CONTATO = ["Pedido de orçamento", "Pedido de catálogo", "Dúvida", "Solicitação de arte", "Balões", "Topo de bolo", "Lembrancinhas", "Locação", "Pós-venda", "Indicação", "Outro"]
ETAPAS_CAPTACAO = [
    "Nova captação", "Convite para WhatsApp enviado", "Aguardando migração",
    "Migrou para WhatsApp", "Em atendimento no WhatsApp", "Orçamento criado",
    "Venda fechada", "Não migrou", "Descartada", "Recusada", "Duplicada", "Spam",
]

ICONE_CANAL = {
    "Instagram": "📸", "Facebook": "📘", "TikTok": "🎵", "YouTube": "▶️",
    "Site / Catálogo": "🌐", "Google": "🔎", "WhatsApp": "🟢",
    "Indicação": "🤝", "Loja física": "🏪", "Outro": "📨",
}


def _agora(now_fn: Callable[[], datetime] | None = None) -> str:
    try:
        return now_fn().strftime("%d/%m/%Y %H:%M") if now_fn else datetime.now().strftime("%d/%m/%Y %H:%M")
    except Exception:
        return datetime.now().strftime("%d/%m/%Y %H:%M")


def _evento(item: Dict[str, Any], descricao: str, now_fn=None) -> None:
    item.setdefault("historico", []).append({"data": _agora(now_fn), "descricao": descricao, "usuario": "Sistema"})
    item["atualizado_em"] = _agora(now_fn)


def _telefone(valor: Any) -> str:
    return re.sub(r"\D", "", str(valor or ""))


def _origem(item: Dict[str, Any]) -> str:
    return str(item.get("canal_origem") or item.get("origem") or item.get("canal") or "Outro")


def _eh_captacao_externa(item: Dict[str, Any]) -> bool:
    return _origem(item) not in ("WhatsApp", "Telefone", "Balcão")


def _etapa(item: Dict[str, Any]) -> str:
    etapa = str(item.get("etapa_captacao") or "").strip()
    if etapa:
        return etapa
    if item.get("numero_proposta"):
        return "Orçamento criado"
    status = str(item.get("status", ""))
    if status in ("Pedido aprovado", "Comprovante recebido", "Arte aprovada", "Em produção", "Pronto", "Entregue"):
        return "Venda fechada"
    return "Nova captação"


def _propostas_por_atendimento(historico: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    mapa: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for proposta in historico or []:
        aid = str(proposta.get("atendimento_id") or "").strip()
        if aid:
            mapa[aid].append(proposta)
    return mapa


def _valor_proposta(proposta: Dict[str, Any]) -> float:
    for chave in ("total", "valor_total", "total_geral"):
        try:
            if proposta.get(chave) not in (None, ""):
                return float(str(proposta.get(chave)).replace(".", "").replace(",", "."))
        except Exception:
            pass
    total = 0.0
    for item in proposta.get("itens", []) or []:
        try:
            qtd = float(item.get("quantidade", 1) or 1)
            vu = float(str(item.get("valor_unitario", item.get("valor", 0))).replace(".", "").replace(",", "."))
            total += qtd * vu
        except Exception:
            continue
    return total


def render_central_oportunidades(
    dados_at: Dict[str, Any],
    salvar_atendimentos: Callable[[Dict[str, Any]], Any],
    historico: List[Dict[str, Any]] | None = None,
    now_fn: Callable[[], datetime] | None = None,
) -> None:
    itens = dados_at.setdefault("itens", [])
    historico = historico or []
    propostas_map = _propostas_por_atendimento(historico)

    st.subheader("🎯 Central de Oportunidades")
    st.caption("Instagram, Facebook, TikTok, YouTube, site e Google captam o interesse. O atendimento comercial é migrado para o WhatsApp sem perder a origem do conteúdo.")

    captacoes = [i for i in itens if _eh_captacao_externa(i)]
    abertas = [i for i in captacoes if _etapa(i) not in ("Venda fechada", "Descartada", "Recusada", "Duplicada", "Spam")]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Novas", sum(_etapa(i) == "Nova captação" for i in abertas))
    c2.metric("Convites enviados", sum(_etapa(i) in ("Convite para WhatsApp enviado", "Aguardando migração") for i in abertas))
    c3.metric("Migraram ao WhatsApp", sum(_etapa(i) in ("Migrou para WhatsApp", "Em atendimento no WhatsApp", "Orçamento criado", "Venda fechada") for i in captacoes))
    c4.metric("Orçamentos", sum(bool(propostas_map.get(str(i.get("id", "")))) or _etapa(i) in ("Orçamento criado", "Venda fechada") for i in captacoes))
    c5.metric("Vendas", sum(_etapa(i) == "Venda fechada" for i in captacoes))

    tab_fila, tab_funil, tab_conteudos = st.tabs(["📥 Fila de captação", "📊 Conversão por canal", "🎬 Conteúdos que geram contatos"])

    with tab_fila:
        f1, f2, f3 = st.columns([2, 1, 1])
        busca = f1.text_input("Pesquisar oportunidade", key="opp_busca").strip().casefold()
        canal = f2.selectbox("Canal de origem", ["Todos"] + CANAIS_CAPTACAO, key="opp_canal")
        etapa_f = f3.selectbox("Etapa", ["Todas"] + ETAPAS_CAPTACAO, key="opp_etapa")

        lista = []
        for item in captacoes:
            texto = " ".join(str(item.get(k, "")) for k in ("cliente", "mensagem", "conteudo_titulo", "campanha", "produto_interesse")).casefold()
            if busca and busca not in texto:
                continue
            if canal != "Todos" and _origem(item) != canal:
                continue
            if etapa_f != "Todas" and _etapa(item) != etapa_f:
                continue
            lista.append(item)
        lista.sort(key=lambda x: (ETAPAS_CAPTACAO.index(_etapa(x)) if _etapa(x) in ETAPAS_CAPTACAO else 99, str(x.get("criado_em", ""))))

        if not lista:
            st.info("Nenhuma oportunidade encontrada.")

        for item in lista:
            origem = _origem(item)
            etapa_atual = _etapa(item)
            titulo = f"{ICONE_CANAL.get(origem, '📨')} {item.get('cliente', 'Contato')} · {etapa_atual}"
            with st.expander(titulo):
                esq, dir_ = st.columns([2, 1])
                with esq:
                    st.write(f"**Mensagem:** {item.get('mensagem') or 'Sem mensagem registrada'}")
                    st.caption(f"Origem: **{origem}** · Tipo: {item.get('tipo_conteudo') or 'Não identificado'} · Motivo: {item.get('motivo_contato') or 'Não classificado'}")
                    if item.get("conteudo_titulo"):
                        st.write(f"**Conteúdo que gerou o contato:** {item.get('conteudo_titulo')}")
                    if item.get("campanha") or item.get("produto_interesse"):
                        st.caption(f"Campanha: {item.get('campanha') or '—'} · Produto: {item.get('produto_interesse') or '—'}")
                    if item.get("conteudo_url"):
                        st.link_button("🔗 Abrir conteúdo original", str(item.get("conteudo_url")), use_container_width=False)
                    st.caption(f"Canal de atendimento: **{item.get('canal_atendimento') or ('WhatsApp' if 'WhatsApp' in etapa_atual else 'Canal de origem')}**")
                with dir_:
                    nova_etapa = st.selectbox("Etapa da captação", ETAPAS_CAPTACAO, index=ETAPAS_CAPTACAO.index(etapa_atual) if etapa_atual in ETAPAS_CAPTACAO else 0, key=f"opp_etapa_{item.get('id')}")
                    motivo = st.selectbox("Motivo do contato", MOTIVOS_CONTATO, index=MOTIVOS_CONTATO.index(item.get("motivo_contato")) if item.get("motivo_contato") in MOTIVOS_CONTATO else 0, key=f"opp_motivo_{item.get('id')}")
                    whatsapp = st.text_input("WhatsApp", value=str(item.get("telefone") or ""), key=f"opp_wa_{item.get('id')}")

                with st.expander("✏️ Fonte da venda / conteúdo", expanded=False):
                    s1, s2 = st.columns(2)
                    tipo = s1.selectbox("Tipo de conteúdo", TIPOS_CONTEUDO, index=TIPOS_CONTEUDO.index(item.get("tipo_conteudo")) if item.get("tipo_conteudo") in TIPOS_CONTEUDO else len(TIPOS_CONTEUDO)-1, key=f"opp_tipo_{item.get('id')}")
                    titulo_conteudo = s2.text_input("Nome do post, Reel, vídeo ou página", value=str(item.get("conteudo_titulo") or ""), key=f"opp_titulo_{item.get('id')}")
                    s3, s4 = st.columns(2)
                    campanha = s3.text_input("Campanha", value=str(item.get("campanha") or ""), key=f"opp_camp_{item.get('id')}")
                    produto = s4.text_input("Produto relacionado", value=str(item.get("produto_interesse") or ""), key=f"opp_prod_{item.get('id')}")
                    url = st.text_input("Link do conteúdo", value=str(item.get("conteudo_url") or ""), key=f"opp_url_{item.get('id')}")

                mensagem_convite = (
                    f"Olá, {item.get('cliente', '').strip() or 'tudo bem'}! 😊 Para enviarmos catálogo, valores e detalhes personalizados, "
                    "continue seu atendimento conosco pelo WhatsApp: "
                )
                texto_entrada = f"Olá! Vim do {origem}"
                if titulo_conteudo.strip():
                    texto_entrada += f", pelo conteúdo {titulo_conteudo.strip()}"
                texto_entrada += ", e gostaria de atendimento/orçamento."
                wa_empresa = ""
                try:
                    wa_empresa = str(st.secrets.get("WHATSAPP_PUBLIC_NUMBER", "")).strip()
                except Exception:
                    pass
                numero_empresa = _telefone(wa_empresa)
                link_destino = f"https://wa.me/{numero_empresa}?text={urllib.parse.quote(texto_entrada)}" if numero_empresa else ""
                convite_completo = mensagem_convite + (link_destino or "[link do WhatsApp da Alphafest]")
                st.text_area("Mensagem para convidar ao WhatsApp", value=convite_completo, key=f"opp_convite_{item.get('id')}", height=95)

                b1, b2, b3, b4 = st.columns(4)
                if b1.button("💾 Salvar", key=f"opp_salvar_{item.get('id')}", use_container_width=True):
                    anterior = etapa_atual
                    item.update({
                        "etapa_captacao": nova_etapa, "motivo_contato": motivo, "telefone": whatsapp.strip(),
                        "tipo_conteudo": tipo, "conteudo_titulo": titulo_conteudo.strip(), "campanha": campanha.strip(),
                        "produto_interesse": produto.strip(), "conteudo_url": url.strip(), "canal_origem": origem,
                    })
                    if anterior != nova_etapa:
                        _evento(item, f"Captação alterada de {anterior} para {nova_etapa}", now_fn)
                    salvar_atendimentos(dados_at)
                    st.rerun()
                if b2.button("📲 Convite enviado", key=f"opp_convite_enviado_{item.get('id')}", use_container_width=True):
                    item.update({"etapa_captacao": "Aguardando migração", "canal_origem": origem, "canal_atendimento": "WhatsApp"})
                    _evento(item, "Convite para continuar o atendimento no WhatsApp enviado", now_fn)
                    salvar_atendimentos(dados_at)
                    st.rerun()
                if b3.button("✅ Migrou ao WhatsApp", key=f"opp_migrou_{item.get('id')}", use_container_width=True):
                    item.update({"etapa_captacao": "Em atendimento no WhatsApp", "canal_origem": origem, "canal_atendimento": "WhatsApp", "canal": "WhatsApp", "telefone": whatsapp.strip()})
                    _evento(item, f"Contato migrado de {origem} para WhatsApp", now_fn)
                    salvar_atendimentos(dados_at)
                    st.rerun()
                if b4.button("🗑️ Descartar", key=f"opp_descartar_{item.get('id')}", use_container_width=True):
                    item["etapa_captacao"] = "Descartada"
                    _evento(item, "Oportunidade descartada", now_fn)
                    salvar_atendimentos(dados_at)
                    st.rerun()

                r1, r2, r3 = st.columns(3)
                if r1.button("🚫 Recusar", key=f"opp_recusar_{item.get('id')}", use_container_width=True):
                    item["etapa_captacao"] = "Recusada"
                    _evento(item, "Oportunidade recusada pela política comercial", now_fn)
                    salvar_atendimentos(dados_at)
                    st.rerun()
                if r2.button("📄 Marcar orçamento", key=f"opp_orcamento_{item.get('id')}", use_container_width=True):
                    item["etapa_captacao"] = "Orçamento criado"
                    _evento(item, "Orçamento criado a partir desta oportunidade", now_fn)
                    salvar_atendimentos(dados_at)
                    st.rerun()
                if r3.button("💰 Marcar venda", key=f"opp_venda_{item.get('id')}", use_container_width=True):
                    item["etapa_captacao"] = "Venda fechada"
                    _evento(item, "Venda fechada a partir desta oportunidade", now_fn)
                    salvar_atendimentos(dados_at)
                    st.rerun()

    with tab_funil:
        linhas = []
        for canal_nome in sorted({_origem(i) for i in captacoes}):
            grupo = [i for i in captacoes if _origem(i) == canal_nome]
            migrados = [i for i in grupo if _etapa(i) in ("Migrou para WhatsApp", "Em atendimento no WhatsApp", "Orçamento criado", "Venda fechada")]
            orcados = [i for i in grupo if _etapa(i) in ("Orçamento criado", "Venda fechada") or propostas_map.get(str(i.get("id", "")))]
            vendas = [i for i in grupo if _etapa(i) == "Venda fechada"]
            faturamento = 0.0
            for i in grupo:
                for p in propostas_map.get(str(i.get("id", "")), []):
                    if p.get("aprovado") or p.get("pago") or p.get("entregue"):
                        faturamento += _valor_proposta(p)
            linhas.append({
                "Canal": canal_nome, "Contatos": len(grupo), "Migraram ao WhatsApp": len(migrados),
                "Orçamentos": len(orcados), "Vendas": len(vendas),
                "Conversão final (%)": round((len(vendas) / len(grupo) * 100), 1) if grupo else 0,
                "Faturamento": faturamento,
            })
        if linhas:
            df = pd.DataFrame(linhas).sort_values(["Vendas", "Contatos"], ascending=False)
            st.dataframe(df, use_container_width=True, hide_index=True, column_config={"Faturamento": st.column_config.NumberColumn(format="R$ %.2f")})
            campeao = df.iloc[0]
            st.success(f"🏆 Canal com melhor resultado registrado: **{campeao['Canal']}** · {int(campeao['Vendas'])} venda(s) · conversão de {campeao['Conversão final (%)']}%.")
        else:
            st.info("Os indicadores aparecerão conforme as oportunidades forem registradas e tratadas.")

    with tab_conteudos:
        agregado: Dict[str, Dict[str, Any]] = {}
        for item in captacoes:
            titulo = str(item.get("conteudo_titulo") or "Conteúdo não identificado").strip()
            chave = f"{_origem(item)}|{titulo}"
            reg = agregado.setdefault(chave, {"Canal": _origem(item), "Conteúdo": titulo, "Contatos": 0, "WhatsApp": 0, "Orçamentos": 0, "Vendas": 0, "Faturamento": 0.0})
            reg["Contatos"] += 1
            if _etapa(item) in ("Migrou para WhatsApp", "Em atendimento no WhatsApp", "Orçamento criado", "Venda fechada"):
                reg["WhatsApp"] += 1
            if _etapa(item) in ("Orçamento criado", "Venda fechada") or propostas_map.get(str(item.get("id", ""))):
                reg["Orçamentos"] += 1
            if _etapa(item) == "Venda fechada":
                reg["Vendas"] += 1
            for p in propostas_map.get(str(item.get("id", "")), []):
                if p.get("aprovado") or p.get("pago") or p.get("entregue"):
                    reg["Faturamento"] += _valor_proposta(p)
        if agregado:
            dfc = pd.DataFrame(agregado.values()).sort_values(["Faturamento", "Vendas", "Contatos"], ascending=False)
            st.dataframe(dfc, use_container_width=True, hide_index=True, column_config={"Faturamento": st.column_config.NumberColumn(format="R$ %.2f")})
        else:
            st.info("Cadastre o nome do post, Reel, vídeo ou página em cada oportunidade para descobrir quais conteúdos colocam dinheiro no caixa.")
