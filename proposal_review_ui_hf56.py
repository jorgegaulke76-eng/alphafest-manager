"""Conferência final do orçamento, sem rede ou persistência de propostas.

O serviço calcula as correções e pontos de atenção. Esta camada mantém somente
o aceite da sessão, vinculado aos dados atuais. O chamador continua responsável
pelo salvamento normal, pelo rerun apropriado e pela limpeza após sucesso.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation

from proposal_review_service_hf56 import assinatura_revisao, conferir_orcamento


_ERROR_MESSAGE = (
    "Não foi possível concluir a conferência deste orçamento. O rascunho foi "
    "preservado. Revise os campos e tente salvar novamente."
)
_CONFIRM_LABEL = "Revisei os pontos de atenção e quero salvar este orçamento"


def _chave(prefixo):
    return f"_{prefixo}_revisao_final"


def _falha_segura():
    return {
        "bloqueios": [{"codigo": "conferencia_indisponivel", "mensagem": _ERROR_MESSAGE}],
        "avisos": [], "resumo": {}, "pode_salvar": False,
    }


def _avaliar(estado, proposta, prefixo, hoje, em_edicao, item_pendente):
    """Recalcula em cada chamada; nunca reaproveita apenas o resultado antigo."""
    erro = False
    try:
        resultado = conferir_orcamento(
            proposta, hoje, em_edicao=em_edicao, item_pendente=item_pendente,
        )
        prova = assinatura_revisao(
            proposta, resultado,
            contexto={"hoje": str(hoje), "em_edicao": bool(em_edicao),
                      "item_pendente": bool(item_pendente)},
        )
    except Exception:
        # Um erro de conferência nunca autoriza gravar nem expõe detalhes
        # internos. Números inválidos normais são tratados pelo serviço.
        resultado, prova, erro = _falha_segura(), None, True

    revisao = estado.get(_chave(prefixo))
    if not revisao or erro or revisao.get("erro") or revisao.get("prova") != prova:
        contador = f"_{prefixo}_sequencia_revisao_final"
        geracao = int(estado.get(contador, 0)) + 1
        estado[contador] = geracao
        revisao = {"geracao": geracao, "prova": prova, "confirmada": False}
        estado[_chave(prefixo)] = revisao
    revisao["resultado"] = deepcopy(resultado)
    revisao["erro"] = erro
    return revisao


def _avisos_exigem_confirmacao(resultado):
    return any(aviso.get("exigir_confirmacao", True) is not False
               for aviso in resultado.get("avisos", []))


def _registrar_confirmacao(estado, prefixo, geracao, widget_key):
    revisao = estado.get(_chave(prefixo))
    if revisao and revisao.get("geracao") == geracao:
        revisao["confirmada"] = estado.get(widget_key) is True


def limpar_revisao(estado, prefixo):
    """Limpa o aceite deste formulário sem reutilizar sua chave de checkbox."""
    estado.pop(_chave(prefixo), None)


def validar_salvamento(ui, proposta, *, prefixo, hoje, em_edicao=False, item_pendente=False):
    """Libera campos válidos e avisos confirmados; não chama rerun ou gravação."""
    revisao = _avaliar(ui.session_state, proposta, prefixo, hoje, em_edicao, item_pendente)
    resultado = revisao["resultado"]
    if revisao["erro"] or resultado.get("bloqueios") or not resultado.get("pode_salvar"):
        return False
    return not _avisos_exigem_confirmacao(resultado) or revisao.get("confirmada") is True


def _numero(valor, *, moeda=False):
    """Formata somente para leitura; um valor ausente não aparece como zero."""
    if valor is None or isinstance(valor, bool):
        return "Revisar"
    try:
        numero = Decimal(str(valor))
        if not numero.is_finite():
            return "Revisar"
        if moeda:
            texto = format(numero, ",.2f").replace(",", "X").replace(".", ",").replace("X", ".")
            return "R$ " + texto
        texto = format(numero, "f")
        if "." in texto:
            texto = texto.rstrip("0").rstrip(".")
        return texto.replace(".", ",")
    except (InvalidOperation, ValueError, TypeError):
        return "Revisar"


def _mostrar_resumo(ui, resumo):
    itens = resumo.get("itens") or []
    if itens:
        linhas = [{
            "Item": int(item.get("indice", indice)) + 1,
            "Produto": str(item.get("produto") or "Produto não informado"),
            "Personalização": str(item.get("especificacoes") or ""),
            "Quantidade": _numero(item.get("quantidade")),
            "Valor unitário": _numero(item.get("valor_unitario"), moeda=True),
            "Total do item": _numero(item.get("total"), moeda=True),
        } for indice, item in enumerate(itens)]
        ui.dataframe(linhas, hide_index=True, width="stretch")
    if resumo:
        ui.caption(
            f"{resumo.get('linhas', 0)} linha(s) · {_numero(resumo.get('unidades'))} unidade(s). "
            "Cada personalização permanece em sua própria linha."
        )
        valores = [{"Condição": rotulo, "Valor": _numero(resumo.get(campo), moeda=True)}
                   for rotulo, campo in (("Subtotal", "subtotal"), ("Desconto", "desconto"),
                                         ("Taxa de entrega", "taxa_entrega"), ("Total", "valor_total"))]
        ui.dataframe(valores, hide_index=True, width="stretch")


def renderizar_revisao(ui, proposta, *, prefixo, hoje, em_edicao=False, item_pendente=False):
    """Mostra correções e pontos de atenção; devolve o resultado da conferência.

    Os bloqueios ficam fora do expander para permanecerem visíveis. Havendo
    apenas avisos legítimos, o operador pode confirmá-los e usar Salvar. Uma nova
    geração de widget impede que um aceite antigo se aplique a dados alterados.
    """
    estado = ui.session_state
    revisao = _avaliar(estado, proposta, prefixo, hoje, em_edicao, item_pendente)
    resultado = revisao["resultado"]
    bloqueios = resultado.get("bloqueios", [])
    avisos = resultado.get("avisos", [])
    precisa_aceite = _avisos_exigem_confirmacao(resultado)

    for bloqueio in bloqueios:
        ui.error(str(bloqueio.get("mensagem") or "Corrija os dados do orçamento antes de salvar."))
    if precisa_aceite and not bloqueios:
        ui.warning("Há pontos de atenção neste orçamento. Confira-os abaixo antes de salvar.")

    with ui.expander("Conferência final do orçamento", expanded=bool(bloqueios or precisa_aceite)):
        _mostrar_resumo(ui, resultado.get("resumo") or {})
        ui.caption("São salvos apenas os itens já adicionados à proposta. Para incluir o item em preenchimento, use Adicionar Item antes de salvar.")
        for aviso in avisos:
            texto = str(aviso.get("mensagem") or "Confira os dados do orçamento.")
            if aviso.get("exigir_confirmacao", True) is False:
                ui.info(texto)
            else:
                ui.warning(texto)

        if bloqueios:
            ui.caption("Corrija os campos indicados antes de salvar. Os itens do rascunho foram mantidos.")
        elif precisa_aceite:
            geracao = revisao["geracao"]
            confirm_key = f"{prefixo}_revisao_final_{geracao}_confirmar"
            revisao["confirmada"] = ui.checkbox(
                _CONFIRM_LABEL, value=bool(revisao.get("confirmada")), key=confirm_key,
                on_change=_registrar_confirmacao,
                args=(estado, prefixo, geracao, confirm_key),
            )
            ui.caption("Depois da revisão, use o botão normal de salvar. Alterar os dados exige uma nova conferência.")
        else:
            ui.caption("Nenhuma correção obrigatória ou ponto de atenção com confirmação. Use o botão normal de salvar.")
    return deepcopy(resultado)
