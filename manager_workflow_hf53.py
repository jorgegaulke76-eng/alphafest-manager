"""Facilidades de formulário HF53, sem Streamlit, persistência ou rede.

O estado pertence à sessão. A edição substitui um item conhecido e a abertura
de outro trabalho só substitui um rascunho depois de uma escolha explícita.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from math import isfinite
from catalogo_orcamento_service import ORCAMENTO_PRODUTO_LIVRE


PENDING_KEY = "_hf53_abertura_pendente"
PROJECT_FIELDS = (
    "cliente", "whatsapp", "necessidade", "ocasiao", "tema", "quantidade",
    "prazo", "limite", "bases", "solucao", "detalhes", "observacoes",
)
QUOTE_FIELDS = (
    "cliente", "documento", "whatsapp", "evento", "observacoes", "desconto",
    "entrega", "prazo", "frete", "taxa_entrega", "validade",
)
SPECIAL_PRICE_FIELDS = (
    "valor_base_oficial", "abatimento_fixo_cliente", "preco_especial_aplicado",
    "perfil_comercial_cliente_id",
)
CATALOG_FIELDS = ("produto_origem", "produto_digitado", "produto_catalogo_id")


def _numero(valor):
    if isinstance(valor, str):
        valor = valor.replace("R$", "").strip()
        if "," in valor:
            valor = valor.replace(".", "").replace(",", ".")
    return float(valor or 0)


def iniciar_edicao(itens, indice):
    if not isinstance(indice, int) or not 0 <= indice < len(itens):
        raise ValueError("O item não está mais nesta proposta. Abra a edição novamente.")
    return {"indice": indice, "original": deepcopy(itens[indice])}


def aplicar_edicao(itens, edicao, *, produto, especificacoes, quantidade, valor_unitario,
                   catalogo_snapshot=None):
    """Devolve outra lista; recusa uma edição cujo item mudou desde a abertura."""
    indice = edicao.get("indice", -1)
    original = edicao.get("original")
    if not isinstance(indice, int) or not 0 <= indice < len(itens) or itens[indice] != original:
        raise ValueError("O item mudou depois de abrir a edição. Cancele e abra o item novamente.")
    nome = str(produto or "").strip()
    if not nome:
        raise ValueError("Informe o produto.")
    try:
        qtd, preco = _numero(quantidade), _numero(valor_unitario)
    except (TypeError, ValueError):
        raise ValueError("Confira a quantidade e o valor unitário.") from None
    if not isfinite(qtd) or qtd <= 0 or not isfinite(preco) or preco < 0:
        raise ValueError("A quantidade deve ser positiva e o valor unitário não pode ser negativo.")

    novo = deepcopy(original)
    produto_mudou = nome != str(original.get("produto") or "").strip()
    preco_mudou = preco != _numero(original.get("valor_unitario"))
    if produto_mudou:
        for campo in CATALOG_FIELDS:
            novo.pop(campo, None)
        novo.update({k: deepcopy(v) for k, v in (catalogo_snapshot or {}).items() if k in CATALOG_FIELDS})
    if produto_mudou or preco_mudou:
        # Não afirmar que uma regra comercial antiga calculou um preço digitado.
        for campo in SPECIAL_PRICE_FIELDS:
            novo.pop(campo, None)
    novo.update(produto=nome, especificacoes=str(especificacoes or ""),
                quantidade=int(qtd) if qtd.is_integer() else qtd, valor_unitario=preco)
    resultado = deepcopy(itens)
    resultado[indice] = novo
    return resultado


def cancelar_edicao(estado, chave):
    """Cancelar descarta somente o editor; itens e identificação não mudam."""
    estado.pop(chave, None)


def chaves_rascunho(estado):
    """Widgets de formulário que devem sobreviver à troca de tela na sessão."""
    campos = {f"form_{c}" for c in QUOTE_FIELDS}
    campos.update(f"anna_modal_{c}" for c in QUOTE_FIELDS)
    campos.update(f"hf53_projeto_{c}" for c in PROJECT_FIELDS)
    for chave in estado:
        # HF55: a consulta do Histórico oculta os widgets do orçamento. Sem
        # preservar a seleção, o retorno pode reconhecer um homônimo e
        # sobrescrever os contatos que foram revisados no rascunho importado.
        texto_chave = str(chave)
        if (texto_chave.startswith(("jorge_orc_cliente_", "anna_orc_cliente_"))
                and texto_chave.endswith("_seletor")):
            campos.add(chave)
        if str(chave).startswith(("hf53_item_", "produto_novo_", "tema_", "nome_item_",
                                 "cor_", "idade_", "obs_item_", "qtd_", "valor_",
                                 "anna_modal_prod_", "anna_modal_tema_", "anna_modal_nome_",
                                 "anna_modal_cor_", "anna_modal_idade_", "anna_modal_obs_",
                                 "anna_modal_qtd_", "anna_modal_valor_")):
            campos.add(chave)
    return [chave for chave in campos if chave in estado]


def _quote_keys(anna=False):
    return ("anna_modal_" if anna else "form_",
            "anna_modal_itens" if anna else "temp_itens",
            "anna_modal_numero_original" if anna else "editar_numero")


def item_em_preenchimento(estado, *, anna=False):
    """HF56: snapshot do item atual que ainda não entrou na lista da proposta.

    Usa somente a geração ativa. Campos de um formulário ainda não submetido
    pelo navegador podem não existir no estado e não são recuperados aqui.
    O snapshot completo invalida um aceite anterior se a digitação mudar.
    """
    sequencia = estado.get("anna_modal_item_key" if anna else "form_key", 0)
    produto_prefixo = f"anna_modal_prod_{sequencia}" if anna else f"produto_novo_{sequencia}"
    inicio = "anna_modal_" if anna else ""
    campos = ("tema", "nome_item", "cor", "idade", "obs" if anna else "obs_item")
    item = {
        "perfil": "anna" if anna else "jorge",
        "sequencia": sequencia,
        "produto_catalogo": str(estado.get(produto_prefixo + "_catalogo") or "").strip(),
        "produto_livre": str(estado.get(produto_prefixo + "_livre") or "").strip(),
        "quantidade": deepcopy(estado.get(f"{inicio}qtd_{sequencia}", 1)),
        "valor_unitario": deepcopy(estado.get(f"{inicio}valor_{sequencia}", 0)),
        "detalhes": {campo: str(estado.get(f"{inicio}{campo}_{sequencia}") or "").strip()
                     for campo in campos},
    }
    escolhido = item["produto_catalogo"]
    ativo = (item["produto_livre"]
             or (escolhido and escolhido != ORCAMENTO_PRODUTO_LIVRE)
             or any(item["detalhes"].values())
             or bool(item["valor_unitario"])
             or item["quantidade"] != 1)
    return item if ativo else None


def possui_rascunho(estado, destino, *, anna=False, hoje=None):
    if destino == "projeto":
        return any(estado.get(f"hf53_projeto_{c}") for c in PROJECT_FIELDS) or bool(estado.get("_projeto_prefill"))
    if destino != "novo_orcamento":
        raise ValueError("Destino de formulário inválido.")
    prefixo, itens_key, numero_key = _quote_keys(anna)
    # Um arquivo incompleto pode trazer somente informações para recuperar
    # manualmente. Elas também são trabalho e precisam da escolha de abertura.
    perfil = "anna" if anna else "jorge"
    pendencias = estado.get(f"_hf57_pendencias_rascunho_{perfil}", {})
    if isinstance(pendencias, dict) and any(
        pendencias.get(campo) for campo in ("item_nao_adicionado", "edicao_item")
    ):
        return True
    if anna and not estado.get(itens_key) and not estado.get(f"anna_modal_iniciado_{estado.get(numero_key) or 'novo'}"):
        return False
    if estado.get(itens_key) or estado.get(numero_key):
        return True
    if any(str(estado.get(prefixo + c) or "").strip()
           for c in ("cliente", "documento", "whatsapp", "evento", "observacoes")):
        return True
    if any(estado.get(prefixo + c, 0) for c in ("desconto", "taxa_entrega")):
        return True
    if estado.get(prefixo + "entrega") not in (None, hoje or date.today()):
        return True
    if estado.get(prefixo + "prazo", "10") != "10" or estado.get(prefixo + "validade", "5") != "5":
        return True
    if estado.get(prefixo + "frete", "Retirada") not in ("Retirada", "Retirada em Itatiba"):
        return True
    return bool(item_em_preenchimento(estado, anna=anna))


def solicitar_abertura(estado, destino, dados, *, anna=False):
    if destino not in ("projeto", "novo_orcamento"):
        raise ValueError("Destino de formulário inválido.")
    if estado.get(PENDING_KEY):
        raise ValueError("Conclua ou cancele a abertura pendente antes de abrir outro trabalho.")
    estado[PENDING_KEY] = {"destino": destino, "dados": deepcopy(dados), "anna": bool(anna)}


def resolver_abertura(estado, escolha, *, hoje=None):
    """Consome uma única intenção. Reruns posteriores não reaplicam os dados.

    'abrir' só é aceito se não há rascunho; 'substituir' é escolha explícita.
    'continuar' abre o rascunho preservado e 'cancelar' não navega.
    """
    pendente = estado.get(PENDING_KEY)
    if not pendente:
        return None
    if escolha not in {"abrir", "substituir", "continuar", "cancelar"}:
        raise ValueError("Escolha de abertura inválida.")
    destino, anna = pendente["destino"], pendente["anna"]
    if escolha == "abrir" and possui_rascunho(estado, destino, anna=anna, hoje=hoje):
        raise ValueError("Há um rascunho. Escolha continuar, substituir ou cancelar.")
    estado.pop(PENDING_KEY)
    if escolha == "cancelar":
        return None
    resposta = {**deepcopy(pendente), "aplicado": escolha != "continuar"}
    if escolha == "continuar":
        return resposta

    dados = pendente["dados"]
    if destino == "projeto":
        for campo in PROJECT_FIELDS:
            estado[f"hf53_projeto_{campo}"] = deepcopy(dados.get(campo, [] if campo == "bases" else ""))
        estado["_hf53_projeto_contexto"] = {"origem": dados.get("origem", "Atendimento"),
                                            "atendimento_id": dados.get("atendimento_id", "")}
        estado.pop("_projeto_prefill", None)
    else:
        prefixo, itens_key, numero_key = _quote_keys(anna)
        perfil = "anna" if anna else "jorge"
        retomada = dados.get("_hf57_retomada") is True
        # Dados externos conservam a identificação digitada até uma escolha
        # explícita de cadastro, inclusive diante de clientes homônimos.
        estado[f"_hf54_cliente_importado_{perfil}"] = bool(dados.get("_hf54_importacao_site")) or retomada
        if retomada:
            estado[f"_hf57_origem_rascunho_{perfil}"] = deepcopy(dados.get("_hf57_origem", {}))
            estado[f"_hf57_pendencias_rascunho_{perfil}"] = deepcopy(dados.get("_hf57_pendencias", {}))
        else:
            estado.pop(f"_hf57_origem_rascunho_{perfil}", None)
            estado.pop(f"_hf57_pendencias_rascunho_{perfil}", None)
        defaults = dict(cliente="", documento="", whatsapp="", evento="", observacoes="",
                        desconto=0.0, entrega=hoje or date.today(), prazo="10", frete="Retirada",
                        taxa_entrega=0.0, validade="5")
        for campo, padrao in defaults.items():
            estado[prefixo + campo] = deepcopy(dados.get(campo, padrao))
        estado[itens_key] = deepcopy(dados.get("itens", []))
        estado[numero_key] = "" if anna else None
        contador = "anna_modal_item_key" if anna else "form_key"
        estado[contador] = int(estado.get(contador, 0)) + 1
        for chave in ("_hf53_edicao_anna" if anna else "_hf53_edicao_jorge",
                      "anna_orc_cliente_novo_seletor" if anna else "jorge_orc_cliente_seletor",
                      "anna_orc_cliente_novo_token" if anna else "jorge_orc_cliente_token"):
            estado.pop(chave, None)
        origem_prefixo = "_anna_hf53" if anna else ""
        # O arquivo portátil abre um orçamento novo. Referências de registros
        # anteriores não voltam como vínculos ativos capazes de alterar dados.
        estado[origem_prefixo + "_atendimento_origem_id"] = "" if retomada else str(dados.get("atendimento_id") or "")
        estado[origem_prefixo + "_projeto_origem_id"] = "" if retomada else str(dados.get("projeto_id") or "")
        if anna:
            estado["anna_modal_iniciado_novo"] = True
            estado["_hf53_anna_contexto_formulario"] = "anna_modal_iniciado_novo"
    return resposta
