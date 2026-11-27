"""Arquivos portáteis de rascunho, sem banco, rede ou gravação de arquivos.

A exportação prepara bytes em memória. A retomada só chama o integrador depois
da revisão do arquivo; ele enfileira a abertura protegida e retorna True. Os
dados do formulário nunca são escritos por esta camada de interface.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re

from proposal_draft_service_hf57 import (
    assinatura_rascunho,
    exportar_rascunho,
    importar_rascunho,
    preparar_retomada,
)


_MAX_UPLOAD = 2 * 1024 * 1024
_CAPTURA_INFO = (
    "O arquivo contém os dados já recebidos pelo Manager. Para incluir o item que "
    "está preenchendo, use Adicionar Item. Para incluir alterações de um item, use "
    "Aplicar alteração do item antes de preparar o arquivo. Campos ainda não "
    "enviados pelo navegador não podem ser recuperados."
)


def _chave(prefixo, area):
    return f"_{prefixo}_rascunho_{area}"


def _geracao(estado, prefixo, area):
    chave = _chave(prefixo, area + "_sequencia")
    numero = int(estado.get(chave, 0)) + 1
    estado[chave] = numero
    return numero


def _erro(erro, padrao):
    return str(erro) if isinstance(erro, ValueError) and str(erro) else padrao


def _numero(valor, *, moeda=False):
    if valor is None or isinstance(valor, bool):
        return "Não informado"
    try:
        numero = Decimal(str(valor))
        if not numero.is_finite():
            return "Revisar"
        texto = format(numero, ",.2f") if moeda else format(numero, "f")
        if moeda:
            return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")
        return (texto.rstrip("0").rstrip(".") if "." in texto else texto).replace(".", ",")
    except (InvalidOperation, ValueError, TypeError):
        return "Revisar"


def _mostrar_itens(ui, itens):
    if not itens:
        ui.info("Este rascunho ainda não tem itens. Você poderá completá-lo no orçamento.")
        return
    ui.dataframe([{
        "Item": indice + 1,
        "Produto": item.get("produto") or "Não informado",
        "Personalização": item.get("especificacoes", ""),
        "Quantidade": _numero(item.get("quantidade")),
        "Valor unitário": _numero(item.get("valor_unitario"), moeda=True),
    } for indice, item in enumerate(itens)], hide_index=True, width="stretch")


def _mostrar_origem(ui, origem):
    rotulos = (("perfil", "Perfil de origem"), ("numero_proposta", "Proposta anterior"),
               ("atendimento_id", "Atendimento de origem"), ("projeto_id", "Projeto de origem"),
               ("criado_em", "Arquivo preparado em"), ("manager_version", "Versão de origem"))
    for campo, rotulo in rotulos:
        if origem.get(campo):
            ui.text(f"{rotulo}: {origem[campo]}")
    ui.caption("As referências de origem não vinculam nem atualizam propostas, atendimentos ou projetos.")


def _mostrar_pendencias(ui, pendencias):
    itens = pendencias.get("item_nao_adicionado") or []
    edicoes = pendencias.get("edicao_item") or []
    if not itens and not edicoes:
        return
    ui.info("Estas informações são para recuperação manual. Não foram adicionadas aos itens nem aplicadas como edição.")
    rotulos = {"tema": "Tema / ocasião", "nome_item": "Nome personalizado", "cor": "Cor / material",
               "idade": "Idade / data", "obs": "Outros detalhes", "obs_item": "Outros detalhes"}
    for indice, item in enumerate(itens, 1):
        with ui.expander(f"Item não adicionado {indice}", expanded=False):
            for campo, rotulo in (("produto_catalogo", "Produto selecionado"), ("produto_livre", "Produto digitado")):
                if item.get(campo):
                    ui.text(f"{rotulo}: {item[campo]}")
            ui.text(f"Quantidade recebida: {_numero(item.get('quantidade'))}")
            ui.text(f"Valor unitário recebido: {_numero(item.get('valor_unitario'), moeda=True)}")
            for campo, valor in (item.get("detalhes") or {}).items():
                if valor:
                    ui.text(f"{rotulos.get(campo, campo)}: {valor}")
    for numero, edicao in enumerate(edicoes, 1):
        with ui.expander(f"Edição pendente {numero} · item {edicao['indice'] + 1}", expanded=False):
            ui.caption("Item original registrado no arquivo")
            _mostrar_itens(ui, [edicao["original"]])
            ui.caption("Últimos campos da edição recebidos pelo Manager; confira antes de aplicar manualmente")
            _mostrar_itens(ui, [edicao["campos"]])


def _mostrar_documento(ui, doc):
    formulario = doc["formulario"]
    ui.text("Cliente: " + (formulario["cliente"] or "Ainda não informado"))
    for campo, rotulo in (("documento", "CPF / CNPJ"), ("whatsapp", "WhatsApp"), ("evento", "Evento")):
        if formulario[campo]:
            ui.text(f"{rotulo}: {formulario[campo]}")
    ui.caption(f"{len(formulario['itens'])} linha(s). Personalizações e metadados permanecem no arquivo.")
    _mostrar_itens(ui, formulario["itens"])
    ui.dataframe([
        {"Condição": "Desconto", "Valor": _numero(formulario["desconto"], moeda=True)},
        {"Condição": "Entrega / retirada", "Valor": formulario["frete"]},
        {"Condição": "Taxa de entrega", "Valor": _numero(formulario["taxa_entrega"], moeda=True)},
        {"Condição": "Data de entrega", "Valor": formulario["entrega"] or "Não informada"},
        {"Condição": "Prazo de produção", "Valor": formulario["prazo"] or "Não informado"},
        {"Condição": "Validade", "Valor": formulario["validade"] or "Não informada"},
    ], hide_index=True, width="stretch")
    if formulario["observacoes"]:
        with ui.expander("Mensagem e observações de origem", expanded=False):
            ui.text(formulario["observacoes"])
    _mostrar_origem(ui, {**doc["origem"], "criado_em": doc["criado_em"], "manager_version": doc["manager_version"]})
    _mostrar_pendencias(ui, doc["pendencias"])
    ui.caption("Identificação, valores, datas, catálogo e condições comerciais serão conferidos no orçamento antes de salvar.")
    with ui.expander("Conteúdo completo do arquivo", expanded=False):
        ui.json(doc, expanded=False)


def renderizar_exportacao(ui, capturar_atual, *, prefixo):
    """Prepara um snapshot explícito e recusa disponibilizar um download antigo."""
    estado = ui.session_state
    chave = _chave(prefixo, "exportacao")
    preparado = estado.get(chave)
    erro_atual = None
    try:
        doc = capturar_atual()
        assinatura = assinatura_rascunho(doc)
    except Exception as exc:
        doc = assinatura = None
        erro_atual = _erro(exc, "Não foi possível preparar o arquivo. O rascunho do formulário foi preservado.")
    if preparado and (erro_atual or preparado["assinatura"] != assinatura):
        preparado["valido"] = False

    with ui.expander("Baixar rascunho", expanded=False):
        ui.caption("Guarde um arquivo para continuar em outra sessão ou computador. Preparar e baixar não salva uma proposta.")
        ui.caption(_CAPTURA_INFO)
        if erro_atual:
            ui.error(erro_atual)
        if ui.button("Preparar arquivo", key=f"{prefixo}_preparar_rascunho", disabled=bool(erro_atual)):
            try:
                dados = exportar_rascunho(doc)
                preparado = {"documento": deepcopy(doc), "dados": dados,
                             "assinatura": assinatura, "valido": True}
                estado[chave] = preparado
            except Exception as exc:
                if preparado:
                    preparado["valido"] = False
                ui.error(_erro(exc, "Não foi possível preparar o arquivo. O rascunho do formulário foi preservado."))
        if not preparado:
            return
        if not preparado["valido"]:
            ui.warning("O rascunho mudou ou não pôde ser conferido depois da preparação. Prepare um novo arquivo antes de baixar.")
            return
        documento = preparado["documento"]
        ui.caption(f"Arquivo preparado em {documento['criado_em']} · {len(documento['formulario']['itens'])} linha(s).")
        if documento["origem"]["numero_proposta"]:
            ui.info("Este arquivo veio da edição da proposta " + documento["origem"]["numero_proposta"]
                    + ". Ao retomar, ele abrirá um novo orçamento; a proposta anterior não será atualizada.")
        pendencias = documento["pendencias"]
        if pendencias["item_nao_adicionado"] or pendencias["edicao_item"]:
            ui.caption("Inclui informações para recuperação manual; elas não serão adicionadas nem aplicadas automaticamente.")
        sufixo = re.sub(r"[^0-9]", "", documento["criado_em"])[:14] or "preparado"
        ui.download_button("Baixar rascunho", preparado["dados"],
                           file_name=f"alphafest-rascunho-{sufixo}.json", mime="application/json",
                           on_click="ignore", key=f"{prefixo}_baixar_rascunho", width="stretch")


def _upload_alterado(estado, prefixo):
    estado[_chave(prefixo, "arquivo_alterado")] = True


def _ler_upload(arquivo):
    tamanho = getattr(arquivo, "size", None)
    if isinstance(tamanho, bool) or not isinstance(tamanho, int) or tamanho < 0:
        raise ValueError("Não foi possível conferir o tamanho do arquivo de rascunho.")
    if tamanho > _MAX_UPLOAD:
        raise ValueError("O arquivo de rascunho ultrapassa o limite de 2 MiB.")
    conteudo = arquivo.getvalue()
    if not isinstance(conteudo, bytes):
        raise ValueError("Envie um arquivo JSON de rascunho válido.")
    if len(conteudo) > _MAX_UPLOAD:
        raise ValueError("O arquivo de rascunho ultrapassa o limite de 2 MiB.")
    return conteudo


def _nova_retomada(estado, prefixo, **dados):
    revisao = {"geracao": _geracao(estado, prefixo, "retomada"),
               "conferida": False, "novo_confirmado": False, "encaminhada": False,
               "erro": None, "retorno": None, **dados}
    estado[_chave(prefixo, "retomada")] = revisao
    return revisao


def _limpar_retomada(estado, prefixo):
    estado.pop(_chave(prefixo, "retomada"), None)
    estado.pop(_chave(prefixo, "arquivo_alterado"), None)
    _geracao(estado, prefixo, "uploader")


def _reabrir_retomada(estado, prefixo):
    revisao = estado.get(_chave(prefixo, "retomada"))
    if revisao:
        _nova_retomada(estado, prefixo, documento=deepcopy(revisao["documento"]),
                       assinatura=revisao["assinatura"], arquivo_hash=revisao["arquivo_hash"],
                       arquivo_nome=revisao["arquivo_nome"])


def _registrar_aceite(estado, prefixo, geracao, campo, widget_key):
    revisao = estado.get(_chave(prefixo, "retomada"))
    if revisao and revisao["geracao"] == geracao:
        revisao[campo] = estado.get(widget_key) is True


def renderizar_retomada(ui, abrir_rascunho, *, prefixo):
    """Valida/revisa o arquivo e solicita abertura; nenhuma proposta é gravada."""
    estado = ui.session_state
    chave = _chave(prefixo, "retomada")
    revisao = estado.get(chave)
    with ui.expander("Retomar rascunho", expanded=False):
        ui.caption("Selecione um arquivo de rascunho para abrir um novo orçamento. A retomada não salva uma proposta.")
        epoca = estado.get(_chave(prefixo, "uploader_sequencia"), 0)
        arquivo = ui.file_uploader("Arquivo de rascunho (.json)", type=["json"],
                                   accept_multiple_files=False, key=f"{prefixo}_arquivo_rascunho_{epoca}",
                                   on_change=_upload_alterado, args=(estado, prefixo))
        mudou = estado.pop(_chave(prefixo, "arquivo_alterado"), False)
        if arquivo is None and mudou:
            estado.pop(chave, None)
            revisao = None
        if arquivo is not None:
            try:
                conteudo = _ler_upload(arquivo)
                arquivo_hash = hashlib.sha256(conteudo).hexdigest()
                nome = str(getattr(arquivo, "name", "rascunho.json"))
                if (mudou or not revisao or revisao.get("arquivo_hash") != arquivo_hash
                        or revisao.get("arquivo_nome") != nome):
                    documento = importar_rascunho(conteudo)
                    revisao = _nova_retomada(
                        estado, prefixo, documento=documento, arquivo_hash=arquivo_hash,
                        arquivo_nome=nome, assinatura=assinatura_rascunho(documento),
                    )
            except Exception as exc:
                revisao = _nova_retomada(
                    estado, prefixo, erro=_erro(exc, "Não foi possível ler o arquivo. O rascunho do formulário foi preservado."),
                )
        if not revisao:
            ui.caption("Aceita arquivos JSON de rascunho de até 2 MiB, inclusive sem itens.")
            return
        ui.button("Limpar revisão do arquivo", key=f"{prefixo}_limpar_revisao",
                  on_click=_limpar_retomada, args=(estado, prefixo))
        if revisao.get("erro"):
            ui.error(revisao["erro"])
            return
        try:
            assinatura = assinatura_rascunho(revisao["documento"])
            if assinatura != revisao["assinatura"]:
                revisao = _nova_retomada(
                    estado, prefixo, documento=deepcopy(revisao["documento"]),
                    assinatura=assinatura, arquivo_hash=revisao["arquivo_hash"], arquivo_nome=revisao["arquivo_nome"],
                )
        except Exception as exc:
            revisao = _nova_retomada(estado, prefixo, erro=_erro(exc, "Não foi possível conferir os dados do arquivo. Reabra a revisão."))
            ui.error(revisao["erro"])
            return
        doc = revisao["documento"]
        ui.text("Arquivo em revisão: " + revisao["arquivo_nome"])
        _mostrar_documento(ui, doc)
        if revisao["encaminhada"]:
            ui.info("Solicitação de retomada encaminhada. Se já havia um rascunho, conclua a escolha apresentada pelo Manager. Nenhuma proposta foi salva por esta ação.")
            ui.button("Reabrir revisão do arquivo", key=f"{prefixo}_reabrir_revisao",
                      on_click=_reabrir_retomada, args=(estado, prefixo))
            return
        geracao = revisao["geracao"]
        conferir_key = f"{prefixo}_retomada_{geracao}_conferida"
        revisao["conferida"] = ui.checkbox(
            "Conferi os dados deste arquivo para retomar o rascunho",
            value=bool(revisao["conferida"]), key=conferir_key,
            on_change=_registrar_aceite, args=(estado, prefixo, geracao, "conferida", conferir_key),
        )
        anterior = doc["origem"]["numero_proposta"]
        if anterior:
            ui.warning("Este arquivo veio da edição da proposta " + anterior + ". A retomada abrirá um NOVO orçamento e não atualizará aquela proposta.")
            novo_key = f"{prefixo}_retomada_{geracao}_novo"
            revisao["novo_confirmado"] = ui.checkbox(
                "Entendi que será um novo orçamento e não atualizará a proposta " + anterior,
                value=bool(revisao["novo_confirmado"]), key=novo_key,
                on_change=_registrar_aceite, args=(estado, prefixo, geracao, "novo_confirmado", novo_key),
            )
        permitido = revisao["conferida"] and (not anterior or revisao["novo_confirmado"])
        if ui.button("Retomar rascunho", key=f"{prefixo}_retomar_rascunho", type="primary", disabled=not permitido):
            if permitido:
                try:
                    dados = preparar_retomada(deepcopy(doc))
                except Exception as exc:
                    revisao["retorno"] = ("error", _erro(exc, "Não foi possível conferir os dados do arquivo. A revisão foi preservada."))
                else:
                    try:
                        aceito = abrir_rascunho(dados)
                    except Exception:
                        revisao["retorno"] = ("error", "Não foi possível solicitar a abertura. A revisão do arquivo foi preservada para outra tentativa.")
                    else:
                        if aceito is True:
                            revisao["encaminhada"] = True
                            revisao["retorno"] = None
                            ui.rerun()
                        else:
                            revisao["retorno"] = ("warning", "A abertura não foi confirmada. A revisão do arquivo continua disponível para outra tentativa.")
        if revisao.get("retorno"):
            tipo, mensagem = revisao["retorno"]
            getattr(ui, tipo)(mensagem)


def _dispensar_referencias(estado, prefixo, geracao, widget_key, dispensar):
    revisao = estado.get(_chave(prefixo, "referencias"))
    if not revisao or revisao["geracao"] != geracao or estado.get(widget_key) is not True:
        return
    try:
        aceito = dispensar()
    except Exception:
        revisao["retorno"] = ("error", "Não foi possível dispensar as informações. Elas continuam disponíveis.")
    else:
        revisao["retorno"] = ("success", "Informações de recuperação manual dispensadas. Os itens do orçamento permanecem como estavam.") if aceito is True else (
            "warning", "A dispensa não foi confirmada. As informações continuam disponíveis.")


def renderizar_referencias(ui, origem, pendencias, *, prefixo, dispensar_pendencias=None, contexto=None):
    """Exibe referências sem ativá-las; a dispensa afeta só as notas manuais."""
    origem, pendencias = origem or {}, pendencias or {}
    estado = ui.session_state
    chave = _chave(prefixo, "referencias")
    tem_pendencias = bool(pendencias.get("item_nao_adicionado") or pendencias.get("edicao_item"))
    revisao = estado.get(chave)
    if not origem and not tem_pendencias:
        # Novo formulário sem referências não herda avisos da dispensa anterior.
        # O contador permanece para não reutilizar uma checkbox já marcada.
        estado.pop(chave, None)
        return
    if revisao and revisao.get("contexto") != contexto:
        estado.pop(chave, None)
        revisao = None
    if tem_pendencias:
        prova = hashlib.sha256(json.dumps({"origem": origem, "pendencias": pendencias, "contexto": contexto},
                                         sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()
        if not revisao or revisao.get("prova") != prova:
            revisao = {"geracao": _geracao(estado, prefixo, "referencias"), "prova": prova,
                       "contexto": deepcopy(contexto), "retorno": None}
            estado[chave] = revisao
    with ui.expander("Informações recuperadas do rascunho", expanded=tem_pendencias):
        if origem:
            _mostrar_origem(ui, origem)
        if revisao and revisao.get("retorno"):
            tipo, mensagem = revisao["retorno"]
            getattr(ui, tipo)(mensagem)
        if not tem_pendencias:
            return
        _mostrar_pendencias(ui, pendencias)
        if dispensar_pendencias is not None:
            widget_key = f"{prefixo}_referencias_{revisao['geracao']}_conferidas"
            conferidas = ui.checkbox("Confirmei a recuperação manual das informações acima", key=widget_key)
            ui.button("Já recuperei estas informações", key=f"{prefixo}_dispensar_pendencias",
                      disabled=not conferidas, on_click=_dispensar_referencias,
                      args=(estado, prefixo, revisao["geracao"], widget_key, dispensar_pendencias))
