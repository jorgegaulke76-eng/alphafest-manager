"""Revisão de uma mensagem do site antes de abrir o orçamento, sem persistência.

O callback apenas enfileira a abertura protegida e retorna True quando aceito.
Só então a interface consome essa tentativa e solicita uma nova execução. Texto
e valores revisados ficam recuperáveis, inclusive se a abertura for cancelada.
"""
from __future__ import annotations

from copy import deepcopy

from site_quote_import_service import analisar_mensagem, assinatura_catalogo, preparar_rascunho


def _desmarcar_conferencia(estado, chave):
    estado[chave] = False


def _mensagem_alterada(estado, widget_key, texto_key, confirm_key):
    estado[texto_key] = estado.get(widget_key, "")
    _desmarcar_conferencia(estado, confirm_key)


def _nova_revisao(estado, chave, analise, *, anterior=None):
    revisao = deepcopy(anterior) if anterior else {
        "analise": deepcopy(analise),
        "itens": deepcopy(analise.get("itens", [])),
        "cliente": "", "whatsapp": "", "evento": "",
    }
    revisao["geracao"] = int(estado.get(chave, {}).get("geracao", 0)) + 1
    revisao["encaminhada"] = False
    revisao["catalogo_alterado"] = False
    revisao.pop("retorno", None)
    estado[chave] = revisao
    return revisao


def _encaminhar_revisao(estado, chave, prefixo, carregar_catalogo, abrir_rascunho):
    """Callback antes do redesenho; lê os valores atuais enviados pelos widgets."""
    revisao = estado.get(chave)
    if not revisao or revisao.get("encaminhada"):
        return
    revisao.pop("retorno", None)
    analise = revisao["analise"]
    widgets = f"{prefixo}_{revisao['geracao']}"
    if estado.get(f"{prefixo}_mensagem", "") != analise.get("texto_original", ""):
        revisao["retorno"] = ("warning", "A mensagem mudou. Analise novamente antes de abrir o orçamento.")
        return
    if not estado.get(f"{widgets}_conferido") or revisao.get("catalogo_alterado") or analise.get("erros"):
        revisao["retorno"] = ("warning", "Confira a revisão atual antes de abrir o orçamento.")
        return
    revisados = []
    for indice, item in enumerate(revisao["itens"]):
        novo = deepcopy(item)
        novo.update(
            quantidade=estado.get(f"{widgets}_qtd_{indice}", item.get("quantidade")),
            valor_unitario=estado.get(f"{widgets}_preco_{indice}", item.get("valor_unitario")),
            especificacoes=estado.get(f"{widgets}_detalhes_{indice}", item.get("especificacoes", "")),
        )
        revisados.append(novo)
    revisao["itens"] = revisados
    for campo in ("cliente", "whatsapp", "evento"):
        revisao[campo] = estado.get(f"{widgets}_{campo}", revisao[campo])
    try:
        catalogo_atual = carregar_catalogo()
        if assinatura_catalogo(catalogo_atual) != analise.get("assinatura_catalogo"):
            revisao["catalogo_alterado"] = True
            estado[f"{widgets}_conferido"] = False
            return
        dados = preparar_rascunho(
            analise, revisados, cliente=revisao["cliente"], whatsapp=revisao["whatsapp"],
            evento=revisao["evento"], confirmar_sem_preco=bool(estado.get(f"{widgets}_sem_preco")),
        )
    except ValueError as erro:
        revisao["retorno"] = ("error", str(erro))
        return
    except Exception:
        revisao["retorno"] = ("error", "Não foi possível conferir o Catálogo online. Sua revisão foi preservada. Tente abrir o rascunho novamente quando a conexão estiver disponível.")
        return
    try:
        aceito = abrir_rascunho(dados)
    except Exception:
        revisao["retorno"] = ("error", "Não foi possível solicitar a abertura do orçamento. Sua revisão foi preservada para outra tentativa.")
        return
    if aceito is not True:
        revisao["retorno"] = ("warning", "A abertura não foi confirmada. Sua revisão continua disponível.")
        return
    revisao["encaminhada"] = True


def renderizar_importacao(ui, carregar_catalogo, abrir_rascunho, *, prefixo="hf54_importar_site"):
    """Recebe Streamlit e dois callbacks; nunca salva proposta, cliente ou catálogo.

    ``carregar_catalogo`` deve retornar uma leitura confirmada e atual do catálogo.
    ``abrir_rascunho(dados)`` deve retornar True após enfileirar a intenção, sem
    chamar rerun. False ou uma exceção conserva a revisão para outra tentativa.
    """
    estado = ui.session_state
    chave = f"_{prefixo}_revisao"
    texto_key = f"_{prefixo}_texto_recebido"
    widget_texto_key = f"{prefixo}_mensagem"
    geracao = int(estado.get(chave, {}).get("geracao", 0))
    confirm_key = f"{prefixo}_{geracao}_conferido"

    with ui.expander("📥 Importar orçamento do site", expanded=False):
        ui.caption("Cole a mensagem recebida pelo WhatsApp. Confira os itens e valores para abrir um rascunho no orçamento.")
        texto = ui.text_area(
            "Mensagem recebida do site", height=190, key=widget_texto_key,
            value=estado.get(texto_key, ""),
            placeholder="1. Nome do produto\nQuantidade: 2\nPersonalização/observações: nome, tema e outros detalhes",
            on_change=_mensagem_alterada, args=(estado, widget_texto_key, texto_key, confirm_key),
        )
        estado[texto_key] = texto
        analisar, cancelar = ui.columns([2, 1])
        clicou_analisar = analisar.button("Analisar mensagem", key=f"{prefixo}_analisar", width="stretch")
        if clicou_analisar:
            try:
                analise = analisar_mensagem(texto, carregar_catalogo())
            except Exception:
                ui.error("Não foi possível analisar a mensagem com o Catálogo atual. Confira a conexão e tente novamente. A revisão anterior foi preservada.")
                return
            _nova_revisao(estado, chave, analise)
        # Desenhar Fechar revisão depois de analisar: o botão já fica habilitado
        # no mesmo rerun que cria a revisão (também no Streamlit AppTest).
        clicou_cancelar = cancelar.button(
            "Fechar revisão", key=f"{prefixo}_cancelar", width="stretch", disabled=chave not in estado,
        )
        if clicou_cancelar:
            estado.pop(chave, None)
            ui.rerun()
            return

        revisao = estado.get(chave)
        if not revisao:
            return
        analise = revisao["analise"]
        geracao = revisao["geracao"]
        widgets = f"{prefixo}_{geracao}"
        confirm_key = f"{widgets}_conferido"

        if texto != analise.get("texto_original", ""):
            ui.warning("A mensagem mudou depois da análise. Clique em Analisar mensagem para conferir o novo conteúdo.")
            return
        if revisao.get("encaminhada"):
            ui.info("Solicitação encaminhada para abertura. Se já havia um rascunho, conclua a escolha apresentada pelo Manager. Nenhuma proposta foi salva por esta importação.")
            if ui.button("Revisar importação novamente", key=f"{widgets}_retomar", width="stretch"):
                _nova_revisao(estado, chave, analise, anterior=revisao)
                ui.rerun()
            return

        if revisao.get("retorno"):
            tipo, mensagem = revisao["retorno"]
            getattr(ui, tipo)(mensagem)

        for aviso in analise.get("avisos", []):
            ui.warning(str(aviso))
        for erro in analise.get("erros", []):
            ui.error(str(erro))
        if analise.get("erros") or not analise.get("itens"):
            ui.caption("Ajuste a mensagem acima e analise novamente antes de abrir o orçamento.")
            return

        ui.caption(f"{len(analise['itens'])} item(ns) identificado(s). Produtos repetidos permanecem em linhas separadas.")
        ui.caption("Os preços reconhecidos são sugestões do Catálogo atual. Confira o preço combinado e o perfil comercial do cliente no orçamento. Para corrigir um produto, ajuste a mensagem e analise novamente.")
        # Os valores ficam também no estado próprio: esconder a revisão ao editar
        # a mensagem não perde ajustes quando Streamlit limpa widgets invisíveis.
        revisados = []
        for indice, item in enumerate(revisao["itens"]):
            base = analise["itens"][indice]
            with ui.expander(f"Item {indice + 1} · {base.get('produto', '')}", expanded=len(analise["itens"]) <= 3):
                ui.text("Produto recebido: " + str(base.get("produto_recebido", base.get("produto", ""))))
                ui.text("Produto no orçamento: " + str(base.get("produto", "")))
                situacao = str(base.get("status_catalogo") or "")
                if situacao in ("encontrado", "alias"):
                    ui.caption("Produto vinculado ao Catálogo." if situacao == "encontrado" else "Nome recebido reconhecido como um alias do Catálogo.")
                else:
                    ui.caption("Produto mantido como texto livre para conferência no orçamento.")
                for aviso in base.get("avisos", []):
                    ui.warning(str(aviso))
                qcol, pcol = ui.columns(2)
                quantidade = item.get("quantidade")
                quantidade = float(quantidade) if quantidade is not None else None
                nova_qtd = qcol.number_input(
                    "Quantidade", min_value=0.0, value=quantidade, step=1.0,
                    placeholder="Informe a quantidade", key=f"{widgets}_qtd_{indice}",
                    on_change=_desmarcar_conferencia, args=(estado, confirm_key),
                )
                novo_preco = pcol.number_input(
                    "Valor unitário (R$)", min_value=0.0, value=float(item.get("valor_unitario") or 0), step=0.5,
                    key=f"{widgets}_preco_{indice}", on_change=_desmarcar_conferencia, args=(estado, confirm_key),
                )
                nova_especificacao = ui.text_area(
                    "Personalização e observações do item", value=str(item.get("especificacoes") or ""), height=100,
                    key=f"{widgets}_detalhes_{indice}", on_change=_desmarcar_conferencia, args=(estado, confirm_key),
                )
                revisado = deepcopy(item)
                revisado.update(quantidade=nova_qtd, valor_unitario=novo_preco, especificacoes=nova_especificacao)
                revisados.append(revisado)
        revisao["itens"] = revisados

        ui.markdown("#### Cliente e evento")
        ui.caption("Preenchimento opcional. Confirme a identificação do cliente no formulário do orçamento.")
        c1, c2 = ui.columns(2)
        revisao["cliente"] = c1.text_input(
            "Nome do cliente", value=revisao["cliente"], key=f"{widgets}_cliente",
            on_change=_desmarcar_conferencia, args=(estado, confirm_key),
        )
        revisao["whatsapp"] = c2.text_input(
            "WhatsApp do cliente", value=revisao["whatsapp"], key=f"{widgets}_whatsapp",
            on_change=_desmarcar_conferencia, args=(estado, confirm_key),
        )
        revisao["evento"] = ui.text_input(
            "Evento", value=revisao["evento"], key=f"{widgets}_evento",
            on_change=_desmarcar_conferencia, args=(estado, confirm_key),
        )

        faltam_quantidades = any(i.get("quantidade") is None or i["quantidade"] <= 0 for i in revisados)
        sem_preco = any(i.get("valor_unitario") == 0 for i in revisados)
        if faltam_quantidades:
            ui.warning("Informe uma quantidade positiva em todos os itens para continuar.")
        confirmar_sem_preco = False
        if sem_preco:
            ui.warning("Há itens com valor unitário zero. Eles precisarão de conferência no orçamento.")
            confirmar_sem_preco = ui.checkbox(
                "Quero abrir com esses itens sem preço e definir os valores no orçamento",
                key=f"{widgets}_sem_preco", on_change=_desmarcar_conferencia, args=(estado, confirm_key),
            )
        if revisao.get("catalogo_alterado"):
            ui.warning("O Catálogo mudou depois da análise. Clique em Analisar mensagem para revisar os produtos e preços atuais.")
        conferido = ui.checkbox("Conferi os itens, as quantidades e os valores desta revisão", key=confirm_key)
        ui.button(
            "Abrir rascunho no orçamento", type="primary", width="stretch", key=f"{widgets}_abrir",
            disabled=not conferido or faltam_quantidades or (sem_preco and not confirmar_sem_preco) or revisao.get("catalogo_alterado", False),
            on_click=_encaminhar_revisao, args=(estado, chave, prefixo, carregar_catalogo, abrir_rascunho),
        )
