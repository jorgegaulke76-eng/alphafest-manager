"""Planejamentos da Central protegida, com a mesma fonte e engines do Manager.

Nenhum acesso a banco, alteração de status ou informação comercial adicional.
O componente recebe Streamlit como argumento para permitir testes offline.
"""
from __future__ import annotations

from central_operational_runtime import montar_snapshot_operacional
from central_producao_painel_hf41 import preparar_fila
from pedido_resumo import resumo_produtos_pedido
from planejamento_diario_hf49 import plano_diario, filtrar
from planejamento_semanal_hf48 import planejar
from roteiro_producao_hf51 import roteiro_diario, agenda_semanal_csv


OPERATIONAL_FIELDS = (
    "numero_proposta", "cliente_nome", "resumo_produtos", "fase_hf41",
    "fase_nome_hf41", "entrega_hf41", "prazo_hf41", "prioridade_hf41",
    "data_texto_hf41",
)


def montar_planejamentos(propostas, tarefas, hoje):
    snapshot = montar_snapshot_operacional(
        propostas, [t for t in (tarefas or []) if isinstance(t, dict) and t.get("ativa", True)],
        [], {}, [], hoje, resumo_produtos=resumo_produtos_pedido, sob_encomenda=True,
    )
    fila = [{campo: p.get(campo) for campo in OPERATIONAL_FIELDS}
            for p in preparar_fila(snapshot["central_producao"], hoje=hoje)]
    return {"diario": plano_diario(fila, hoje=hoje), "semanal": planejar(fila, hoje=hoje)}


def renderizar_planejamentos(ui, planos, abrir_pedido, *, prefixo="anna_hf53"):
    diario, semanal = planos["diario"], planos["semanal"]
    hoje = diario["hoje"]
    with ui.expander("☀️ Planejamento diário · prioridades de produção", expanded=False):
        ui.caption("Pedidos aprovados e ainda abertos, conforme Histórico e Fluxo. Produção sob encomenda.")
        grupos = diario["grupos"]
        colunas = ui.columns(4)
        for coluna, grupo in zip(colunas, ("Atrasados", "Hoje", "Amanhã", "Sem prazo")):
            coluna.metric(grupo, len(grupos[grupo]))
        if diario["prontos_urgentes"]:
            ui.info(f"{diario['prontos_urgentes']} pedido(s) urgente(s) pronto(s): combinar retirada ou entrega.")
        grupo = ui.selectbox("Ver situação", list(grupos), key=f"{prefixo}_grupo")
        busca = ui.text_input("Buscar nos pedidos desta situação", placeholder="Número, cliente ou produto", key=f"{prefixo}_busca")
        encontrados = filtrar(grupos[grupo], busca)
        paginas = max(1, (len(encontrados) + 7) // 8)
        pagina = int(ui.number_input("Página do planejamento", min_value=1, max_value=paginas,
                                    value=1, step=1, key=f"{prefixo}_pagina_{grupo}_{paginas}"))
        ui.caption(f"{len(encontrados)} pedido(s) · página {pagina} de {paginas}")
        if not encontrados:
            ui.success("Nenhum pedido nesta seleção.")
        for pos, pedido in enumerate(encontrados[(pagina - 1) * 8:pagina * 8]):
            numero = str(pedido.get("numero_proposta") or "")
            info, acao = ui.columns([5, 2])
            info.write(f"{numero or 'Sem número'} · {pedido.get('cliente_nome') or 'Cliente'}")
            info.caption(f"{pedido['data_texto_hf41']} · {pedido['fase_nome_hf41']} · {pedido['acao_hf49']}")
            info.caption(pedido.get("resumo_produtos") or "Itens não informados")
            if acao.button("Abrir pedido", key=f"{prefixo}_abrir_diario_{pagina}_{pos}_{numero}",
                           disabled=not numero, width="stretch"):
                abrir_pedido(numero)
        ui.download_button(
            "📥 Baixar roteiro do dia (.txt)",
            data=roteiro_diario(diario, incluir_retornos=False).encode("utf-8"),
            file_name=f"alphafest_roteiro_do_dia_{hoje:%Y%m%d}.txt", mime="text/plain",
            key=f"{prefixo}_baixar_txt",
        )

    with ui.expander("📅 Planejamento semanal · próximas 7 datas", expanded=False):
        c1, c2, c3 = ui.columns(3)
        c1.metric("Entregas na semana", semanal["total_semana"])
        c2.metric("Dias com entregas", semanal["dias_com_entregas"])
        c3.metric("Pendências vencidas", len(semanal["vencidos"]))
        ui.dataframe([{"Data": d["data"].strftime("%d/%m/%Y"), "Entregas previstas": d["total"]}
                      for d in semanal["dias"]], hide_index=True, width="stretch")
        dias = [d for d in semanal["dias"] if d["total"]]
        if dias:
            indice = ui.selectbox("Ver pedidos da data", list(range(len(dias))),
                                 format_func=lambda i: dias[i]["data"].strftime("%d/%m/%Y"),
                                 key=f"{prefixo}_dia_semana")
            pedidos = dias[indice]["pedidos"]
            pedido_indice = ui.selectbox("Pedido previsto", list(range(len(pedidos))),
                                        format_func=lambda i: f"{pedidos[i].get('numero_proposta')} · {pedidos[i].get('cliente_nome')} · {pedidos[i].get('fase_nome_hf41')}",
                                        key=f"{prefixo}_pedido_semana_{indice}")
            numero = str(pedidos[pedido_indice].get("numero_proposta") or "")
            if ui.button("Abrir pedido da semana", key=f"{prefixo}_abrir_semanal", disabled=not numero):
                abrir_pedido(numero)
        else:
            ui.info("Nenhum pedido com entrega prevista nos próximos sete dias.")
        if semanal["sem_data"]:
            ui.caption(f"{len(semanal['sem_data'])} pedido(s) sem data: conferir o prazo no planejamento diário.")
        ui.download_button(
            "📥 Baixar agenda da semana (.csv)", data=agenda_semanal_csv(semanal),
            file_name=f"alphafest_agenda_semanal_{hoje:%Y%m%d}.csv", mime="text/csv",
            key=f"{prefixo}_baixar_csv",
        )
        ui.caption("As contagens representam pedidos, não horas ou capacidade de produção. A agenda oficial e seus PDFs continuam abaixo.")
