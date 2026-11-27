"""Central de Oportunidades da Alphafest.

Módulo isolado: qualquer falha aqui não impede o atendimento operacional.
Ele trabalha sobre o mesmo documento de atendimentos, sem migração destrutiva.
"""
from __future__ import annotations

import re
import urllib.parse
from collections import defaultdict
from datetime import datetime

from encerramento_sem_retorno_hf64 import elegibilidade_encerramento
from retornos_sem_envio_hf63 import listar_sem_registro_envio
from thu_comercial_service import montar_retornos_comerciais
from proposal_status import status_bool, proposta_encerrada
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


def _telefone_chave(valor: Any) -> str:
    """Compara WhatsApp apenas quando existe número suficientemente completo."""
    digitos = _telefone(valor)
    if digitos.startswith("55") and len(digitos) > 11:
        digitos = digitos[2:]
    return digitos if 10 <= len(digitos) <= 11 else ""


def diagnosticar_vinculos_propostas(
    atendimentos: List[Dict[str, Any]],
    historico: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Diagnóstico sem escrita: vínculos ausentes/quebrados e pistas por telefone.

    O telefone serve somente como pista; NUNCA cria ou confirma vínculo sozinho.
    """
    ids = {str(i.get("id") or "").strip() for i in atendimentos if isinstance(i, dict)}
    ids.discard("")
    fontes = defaultdict(list)
    for item in atendimentos:
        if not isinstance(item, dict):
            continue
        chave = _telefone_chave(item.get("telefone") or item.get("whatsapp"))
        if chave:
            fontes[chave].append(item)

    ausentes = []
    invalidos = []
    pistas = []
    for proposta in historico:
        if not isinstance(proposta, dict):
            continue
        aid = str(proposta.get("atendimento_id") or "").strip()
        if aid in ids:
            continue
        if aid:
            invalidos.append(proposta)
        else:
            ausentes.append(proposta)
        chave = _telefone_chave(proposta.get("whatsapp") or proposta.get("cliente_wa"))
        candidatos = fontes.get(chave, []) if chave else []
        if candidatos:
            pistas.append({
                "numero_proposta": str(proposta.get("numero_proposta") or "Sem número"),
                "candidatos": [
                    {"id": str(i.get("id") or ""), "origem": _origem(i)}
                    for i in candidatos
                ],
            })
    return {"sem_vinculo": len(ausentes), "vinculo_invalido": len(invalidos),
            "pistas": pistas}


def _origem(item: Dict[str, Any]) -> str:
    return str(item.get("canal_origem") or item.get("origem") or item.get("canal") or "Outro")


def _eh_captacao_externa(item: Dict[str, Any]) -> bool:
    return _origem(item) not in ("WhatsApp", "Telefone", "Balcão", "Não informado")


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


def _propostas_aprovadas(item: Dict[str, Any], propostas_map: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Venda confirmada exige aprovação oficial e vínculo explícito ao atendimento."""
    vinculadas = propostas_map.get(str(item.get("id") or ""), [])
    return [
        p for p in vinculadas
        if status_bool(p, "aprovado") and not proposta_encerrada(p)
    ]


def _tem_orcamento_vinculado(item: Dict[str, Any], propostas_map: Dict[str, List[Dict[str, Any]]]) -> bool:
    return bool(propostas_map.get(str(item.get("id") or "")))


def _tem_venda_confirmada(item: Dict[str, Any], propostas_map: Dict[str, List[Dict[str, Any]]]) -> bool:
    return bool(_propostas_aprovadas(item, propostas_map))


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
    abrir_orcamento: Callable[[Dict[str, Any]], Any] | None = None,
    registrar_envio: Callable[[str], Any] | None = None,
    encerrar_sem_retorno: Callable[[str], Any] | None = None,
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
    c4.metric("Orçamentos vinculados", sum(_tem_orcamento_vinculado(i, propostas_map) for i in captacoes))
    c5.metric("Vendas confirmadas", sum(_tem_venda_confirmada(i, propostas_map) for i in captacoes))
    st.caption(
        "Orçamentos e vendas confirmadas exigem vínculo com o Histórico pelo atendimento_id; "
        "venda exige aprovação oficial. Etapas marcadas manualmente não aumentam esses totais."
    )

    # Diagnóstico da ligação real entre captação, WhatsApp e proposta.
    # Eventos anônimos do site são métricas, não cadastros de clientes.
    sem_whatsapp = [i for i in abertas if not _telefone(i.get("telefone") or i.get("whatsapp"))]
    sem_conteudo = [i for i in abertas if not str(i.get("conteudo_titulo") or "").strip()]
    sem_vinculo = [
        i for i in captacoes
        if _etapa(i) in ("Orçamento criado", "Venda fechada")
        and not _tem_orcamento_vinculado(i, propostas_map)
    ]
    vendas_sem_confirmacao = [
        i for i in captacoes
        if _etapa(i) == "Venda fechada" and not _tem_venda_confirmada(i, propostas_map)
    ]
    with st.expander("🔎 Conferência da origem e dos vínculos comerciais", expanded=False):
        st.caption(
            "Confira os registros de atendimentos reais antes de interpretar o funil. "
            "Visitas e cliques anônimos no site não são clientes, mensagens recebidas, orçamentos ou vendas."
        )
        q1, q2, q3 = st.columns(3)
        q1.metric("Sem WhatsApp no atendimento", len(sem_whatsapp))
        q2.metric("Sem conteúdo de origem", len(sem_conteudo))
        q3.metric("Etapa comercial sem proposta vinculada", len(sem_vinculo))
        st.metric("Vendas marcadas sem aprovação vinculada", len(vendas_sem_confirmacao))
        st.caption(
            "Vínculo de proposta significa que o Histórico contém atendimento_id correspondente. "
            "Uma etapa marcada manualmente não comprova, por si só, que existe orçamento vinculado ou venda aprovada."
        )
        for registro in sem_vinculo[:10]:
            st.write(
                "• "
                + str(registro.get("cliente") or "Contato sem identificação")
                + " · " + _origem(registro)
                + " · " + _etapa(registro)
                + " — conferir associação da proposta no Histórico"
            )
        if len(sem_vinculo) > 10:
            st.caption("Exibindo os primeiros 10 vínculos a conferir.")
        if not (sem_whatsapp or sem_conteudo or sem_vinculo or vendas_sem_confirmacao):
            st.success("Os atendimentos externos cadastrados não apresentam pendências nessas quatro conferências.")
        diagnostico_propostas = diagnosticar_vinculos_propostas(itens, historico)
        st.markdown("#### 📄 Propostas do Histórico sem vínculo válido")
        v1, v2 = st.columns(2)
        v1.metric("Sem atendimento vinculado", diagnostico_propostas["sem_vinculo"])
        v2.metric("Referência a atendimento não encontrado", diagnostico_propostas["vinculo_invalido"])
        st.caption(
            "Nem todo orçamento precisa ter uma origem digital. Essas contagens não significam erro "
            "nem diminuem vendas confirmadas no Histórico; indicam apenas que não é possível atribuir "
            "a proposta a um atendimento desta Central."
        )
        if diagnostico_propostas["pistas"]:
            st.markdown("**Possíveis correspondências para conferência manual**")
            for pista in diagnostico_propostas["pistas"][:10]:
                candidatos_txt = ", ".join(
                    str(c["id"]) + " (" + str(c["origem"]) + ")"
                    for c in pista["candidatos"][:3]
                )
                st.write(
                    "• Proposta " + pista["numero_proposta"]
                    + " · possível atendimento: " + candidatos_txt
                )
            st.caption(
                "Correspondências usam apenas número de WhatsApp; não comprovam que se trata "
                "do mesmo pedido. Nenhum vínculo é criado por esta conferência."
            )
        st.info(
            "Para novos orçamentos, inicie a proposta pela Caixa unificada, usando a ação "
            "Orçamento no atendimento correspondente. Isso preserva a origem sem precisar "
            "adivinhar a associação depois."
        )

        st.info(
            "Fluxo correto: identificar um contato real → registrar o canal de origem "
            "→ continuar o atendimento no WhatsApp → vincular o orçamento real "
            "→ confirmar a venda somente após aprovação. Nenhuma etapa é avançada automaticamente."
        )

    tab_fila, tab_funil, tab_conteudos, tab_retornos = st.tabs(["📥 Fila de captação", "📊 Conversão por canal", "🎬 Conteúdos que geram contatos", "🔔 Retornos de orçamentos"])

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
                        st.link_button("🔗 Abrir conteúdo original", str(item.get("conteudo_url")), width="content")
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
                if b1.button("💾 Salvar", key=f"opp_salvar_{item.get('id')}", width="stretch"):
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
                if b2.button("📲 Convite enviado", key=f"opp_convite_enviado_{item.get('id')}", width="stretch"):
                    item.update({"etapa_captacao": "Aguardando migração", "canal_origem": origem, "canal_atendimento": "WhatsApp"})
                    _evento(item, "Convite para continuar o atendimento no WhatsApp enviado", now_fn)
                    salvar_atendimentos(dados_at)
                    st.rerun()
                if b3.button("✅ Migrou ao WhatsApp", key=f"opp_migrou_{item.get('id')}", width="stretch"):
                    item.update({"etapa_captacao": "Em atendimento no WhatsApp", "canal_origem": origem, "canal_atendimento": "WhatsApp", "canal": "WhatsApp", "telefone": whatsapp.strip()})
                    _evento(item, f"Contato migrado de {origem} para WhatsApp", now_fn)
                    salvar_atendimentos(dados_at)
                    st.rerun()
                if b4.button("🗑️ Descartar", key=f"opp_descartar_{item.get('id')}", width="stretch"):
                    item["etapa_captacao"] = "Descartada"
                    _evento(item, "Oportunidade descartada", now_fn)
                    salvar_atendimentos(dados_at)
                    st.rerun()

                # Abre o formulário oficial preservando atendimento_id e origem.
                # Não cria proposta ao clicar; a gravação continua no orçamento.
                if abrir_orcamento is not None:
                    possui_proposta = _tem_orcamento_vinculado(item, propostas_map)
                    if possui_proposta:
                        st.caption(
                            "📄 Este atendimento já possui proposta vinculada. "
                            "Consulte o Histórico antes de criar outra."
                        )
                    if st.button(
                        "➕ Criar orçamento a partir deste atendimento",
                        key=f"opp_novo_orcamento_{item.get('id')}",
                        disabled=possui_proposta or not str(item.get("id") or "").strip(),
                        width="stretch",
                        help="Abre a criação oficial com cliente, WhatsApp, mensagem e vínculo do atendimento.",
                    ):
                        abrir_orcamento({
                            "cliente": str(item.get("cliente") or ""),
                            "whatsapp": str(item.get("telefone") or ""),
                            "observacoes": str(item.get("mensagem") or ""),
                            "atendimento_id": str(item.get("id") or ""),
                        })

                r1, r2, r3 = st.columns(3)
                if r1.button("🚫 Recusar", key=f"opp_recusar_{item.get('id')}", width="stretch"):
                    item["etapa_captacao"] = "Recusada"
                    _evento(item, "Oportunidade recusada pela política comercial", now_fn)
                    salvar_atendimentos(dados_at)
                    st.rerun()
                if r2.button(
                    "📄 Marcar orçamento", key=f"opp_orcamento_{item.get('id')}",
                    width="stretch", disabled=not _tem_orcamento_vinculado(item, propostas_map),
                    help="Disponível quando houver uma proposta real no Histórico vinculada a este atendimento.",
                ):
                    item["etapa_captacao"] = "Orçamento criado"
                    _evento(item, "Orçamento criado a partir desta oportunidade", now_fn)
                    salvar_atendimentos(dados_at)
                    st.rerun()
                if r3.button(
                    "💰 Marcar venda", key=f"opp_venda_{item.get('id')}",
                    width="stretch", disabled=not _tem_venda_confirmada(item, propostas_map),
                    help="Somente após aprovação oficial de proposta vinculada no Histórico.",
                ):
                    item["etapa_captacao"] = "Venda fechada"
                    _evento(item, "Venda fechada a partir desta oportunidade", now_fn)
                    salvar_atendimentos(dados_at)
                    st.rerun()

    with tab_funil:
        linhas = []
        for canal_nome in sorted({_origem(i) for i in captacoes}):
            grupo = [i for i in captacoes if _origem(i) == canal_nome]
            migrados = [i for i in grupo if _etapa(i) in ("Migrou para WhatsApp", "Em atendimento no WhatsApp", "Orçamento criado", "Venda fechada")]
            orcados = [i for i in grupo if _tem_orcamento_vinculado(i, propostas_map)]
            vendas = [i for i in grupo if _tem_venda_confirmada(i, propostas_map)]
            faturamento = sum(
                _valor_proposta(p)
                for i in grupo for p in _propostas_aprovadas(i, propostas_map)
            )
            linhas.append({
                "Canal": canal_nome, "Contatos": len(grupo), "Migraram ao WhatsApp": len(migrados),
                "Orçamentos": len(orcados), "Vendas": len(vendas),
                "Conversão final (%)": round((len(vendas) / len(grupo) * 100), 1) if grupo else 0,
                "Faturamento": faturamento,
            })
        if linhas:
            df = pd.DataFrame(linhas).sort_values(["Vendas", "Contatos"], ascending=False)
            st.dataframe(df, width="stretch", hide_index=True, column_config={"Faturamento": st.column_config.NumberColumn(format="R$ %.2f")})
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
            if _tem_orcamento_vinculado(item, propostas_map):
                reg["Orçamentos"] += 1
            if _tem_venda_confirmada(item, propostas_map):
                reg["Vendas"] += 1
            for p in _propostas_aprovadas(item, propostas_map):
                reg["Faturamento"] += _valor_proposta(p)
        if agregado:
            dfc = pd.DataFrame(agregado.values()).sort_values(["Faturamento", "Vendas", "Contatos"], ascending=False)
            st.dataframe(dfc, width="stretch", hide_index=True, column_config={"Faturamento": st.column_config.NumberColumn(format="R$ %.2f")})
        else:
            st.info("Cadastre o nome do post, Reel, vídeo ou página em cada oportunidade para descobrir quais conteúdos colocam dinheiro no caixa.")

    with tab_retornos:
        st.markdown("#### 📋 Orçamentos sem registro de envio")
        st.caption(
            "Estes orçamentos ainda não têm envio registrado no Manager. "
            "Isso NÃO significa que o cliente não recebeu a proposta. "
            "A confirmação abaixo não envia mensagem e não marca venda."
        )
        propostas_sem_envio = listar_sem_registro_envio(historico)
        st.metric("Propostas sem registro de envio", len(propostas_sem_envio))
        if propostas_sem_envio:
            busca_sem_envio = st.text_input(
                "Localizar proposta sem registro de envio",
                placeholder="Número ou nome do cliente",
                key="hf63_busca_sem_envio",
            ).strip().casefold()
            filtradas_sem_envio = [
                p for p in propostas_sem_envio
                if not busca_sem_envio or busca_sem_envio in (
                    str(p.get("numero_proposta") or "") + " "
                    + str(p.get("cliente_nome") or p.get("cliente") or "")
                ).casefold()
            ]
            st.caption(
                f"{len(filtradas_sem_envio)} proposta(s) encontrada(s). "
                "Mostrando até 30 por página para manter o Manager leve."
            )
            total_paginas = max(1, (len(filtradas_sem_envio) + 29) // 30)
            pagina_sem_envio = st.number_input(
                "Página das propostas sem registro",
                min_value=1,
                max_value=total_paginas,
                value=1,
                step=1,
                key="hf63_pagina_sem_envio",
            ) if total_paginas > 1 else 1
            inicio_sem_envio = (int(pagina_sem_envio) - 1) * 30
            for proposta_sem in filtradas_sem_envio[inicio_sem_envio:inicio_sem_envio + 30]:
                numero_sem = str(proposta_sem.get("numero_proposta") or "").strip()
                nome_sem = str(proposta_sem.get("cliente_nome") or proposta_sem.get("cliente") or "Cliente")
                data_sem = str(proposta_sem.get("data_geracao") or proposta_sem.get("data") or "Data não informada")
                with st.expander(f"📄 {numero_sem} · {nome_sem} · {data_sem}"):
                    st.info(
                        "Confira primeiro a conversa real no WhatsApp. "
                        "Só registre se o orçamento já foi efetivamente enviado ao cliente."
                    )
                    if registrar_envio is None:
                        st.caption("Para registrar o envio, abra esta proposta em Operação → Histórico.")
                    else:
                        ciente_sem = st.checkbox(
                            "Confirmo que enviei este orçamento ao cliente",
                            key=f"hf63_confirmar_envio_{numero_sem}",
                        )
                        if st.button(
                            "✅ Registrar envio já realizado",
                            key=f"hf63_registrar_envio_{numero_sem}",
                            disabled=not ciente_sem,
                            width="stretch",
                        ):
                            ok_envio, _proposta_atual, msg_envio = registrar_envio(numero_sem)
                            if ok_envio:
                                st.success(f"Envio confirmado para a proposta {numero_sem}.")
                                st.rerun()
                            else:
                                st.error(msg_envio or "Não foi possível confirmar o registro.")
        else:
            st.success(
                "Não foram encontradas propostas abertas sem registro de envio. "
                "Consulte abaixo os retornos das propostas já registradas."
            )
        st.divider()
        st.markdown("#### 🔔 Lembretes de orçamentos enviados")
        st.caption(
            "Acompanhamento assistido, calculado a partir das propostas reais do Histórico. "
            "Não envia WhatsApp ou Telegram, não registra um contato e não altera pedidos."
        )
        hoje = (now_fn() if now_fn else datetime.now()).date()
        retornos = montar_retornos_comerciais(historico, hoje, limite=200)
        agir = [item for item in retornos if item.get("nivel") != "aguardar"]
        alta = sum(item.get("nivel") in ("alta", "urgente") for item in agir)
        c1, c2, c3 = st.columns(3)
        c1.metric("Retornos a conferir", len(agir))
        c2.metric("Prioridade alta ou urgente", alta)
        c3.metric("Aguardar cliente", len(retornos) - len(agir))
        if agir:
            resumo = [
                "ALPHAFEST | RETORNOS COMERCIAIS A CONFERIR",
                "Gerado em: " + hoje.strftime("%d/%m/%Y"),
                "Pendentes: " + str(len(agir)),
                "Alta prioridade: " + str(alta),
                "",
                "Lista operacional sem nomes, telefones, valores ou mensagens de clientes:",
            ]
            for item in agir:
                numero = str(item.get("numero_proposta") or "Sem número")
                resumo.append(
                    "Proposta " + numero
                    + " | Prioridade: " + str(item.get("nivel") or "normal")
                    + " | Dias desde último envio: " + str(item.get("dias_sem_retorno") or 0)
                    + " | Ação: " + str(item.get("acao") or "Conferir atendimento")
                )
            resumo.append("")
            resumo.append("Confira os detalhes no Manager antes de qualquer contato. Nenhuma mensagem foi enviada.")
            st.download_button(
                "📥 Baixar resumo de retornos (.txt)",
                data="\n".join(resumo).encode("utf-8"),
                file_name="alphafest-retornos-comerciais.txt",
                mime="text/plain",
                key="opp_retornos_resumo_txt",
            )
        if not agir:
            st.info("Nenhum orçamento com envio registrado precisa de acompanhamento neste momento.")
            st.caption(
                "A fila considera somente propostas marcadas como enviadas no Histórico. "
                "Propostas sem esse registro não entram no acompanhamento, mesmo que já tenham sido criadas. "
                "Depois de realmente enviar o orçamento ao cliente, use **Registrar envio** "
                "no Histórico da proposta (disponível para Jorge). "
                "Não marque como enviado um orçamento que ainda não foi encaminhado."
            )
        else:
            st.caption("Confira o histórico da conversa antes de retomar. Os prazos são sugestões operacionais, não confirmação de silêncio do cliente.")
            for item in agir:
                numero = str(item.get("numero_proposta") or "—")
                cliente = str(item.get("cliente_nome") or "Cliente")
                with st.expander(f"{item.get('nivel', 'normal').upper()} · Proposta {numero} · {cliente}"):
                    st.write(item.get("motivo") or "Revisar o orçamento enviado.")
                    st.write("**Próxima ação:** " + str(item.get("acao") or "Conferir atendimento"))
                    st.caption("Último envio registrado: " + str(item.get("ultimo_contato_em") or "Não informado"))
                    st.text_area(
                        "Mensagem sugerida para revisão manual",
                        value=str(item.get("mensagem_sugerida") or ""),
                        key=f"opp_retorno_msg_{numero}",
                        height=95,
                    )
                    st.caption("Copie a mensagem apenas após conferir o atendimento. Nenhum contato é enviado automaticamente.")
                    # HF64: somente uma decisao manual e rastreavel; tempo decorrido
                    # nao e evidencia de ausencia de resposta.
                    proposta_atual_hf64 = next(
                        (p for p in historico
                         if str((p or {}).get("numero_proposta") or "").strip() == numero),
                        None,
                    )
                    elegivel_hf64, _ = elegibilidade_encerramento(proposta_atual_hf64, hoje)
                    if encerrar_sem_retorno is not None and elegivel_hf64:
                        with st.expander("📦 Encerrar orçamento sem retorno (manual)"):
                            st.warning(
                                "Use somente depois de conferir a conversa real: "
                                "o prazo sozinho não comprova que o cliente deixou de responder. "
                                "Esta ação preserva a proposta no Histórico e retira da fila de retornos."
                            )
                            confirmar_sem_retorno_hf64 = st.checkbox(
                                "Conferi a conversa e confirmo que não houve retorno e que não virou pedido",
                                key=f"hf64_confirmar_sem_retorno_{numero}",
                            )
                            if st.button(
                                "📦 Marcar como não fechado — sem retorno",
                                key=f"hf64_encerrar_sem_retorno_{numero}",
                                disabled=not confirmar_sem_retorno_hf64,
                                width="stretch",
                            ):
                                ok_hf64, motivo_hf64 = encerrar_sem_retorno(numero)
                                if ok_hf64:
                                    st.success("Proposta encerrada comercialmente. Histórico preservado.")
                                    st.rerun()
                                else:
                                    st.error(motivo_hf64 or "Não foi possível encerrar a proposta.")
