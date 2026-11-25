"""Conferência de propostas semelhantes, restrita ao estado da sessão.

A consulta não cria, modifica, mescla ou exclui propostas. O salvamento do
Manager só continua quando ``validar_salvamento`` confirmar a leitura atual
e, havendo candidatos, a conferência vinculada aos dados que serão salvos.
"""
from __future__ import annotations

from copy import deepcopy

from proposal_duplicate_service_hf55 import (
    analisar_duplicidades,
    assinatura_conferencia,
    assinatura_proposta,
)


_READ_ERROR = (
    "Não foi possível conferir as propostas recentes. Seu rascunho foi preservado. "
    "Confira a conexão e tente novamente antes de salvar."
)


def _chave(prefixo):
    return f"_{prefixo}_conferencia_duplicidades"


def _nova_revisao(estado, prefixo, proposta_assinatura, hoje, *, resultado=None, prova=None, erro=None):
    contador = f"_{prefixo}_sequencia_duplicidades"
    geracao = int(estado.get(contador, 0)) + 1
    estado[contador] = geracao
    revisao = {
        "proposta_assinatura": proposta_assinatura,
        "hoje": str(hoje),
        "geracao": geracao,
        "resultado": deepcopy(resultado),
        "prova": prova,
        "erro": erro,
        "confirmada": False,
    }
    estado[_chave(prefixo)] = revisao
    return revisao


def _contexto(estado, proposta, prefixo, hoje):
    assinatura = assinatura_proposta(proposta)
    revisao = estado.get(_chave(prefixo))
    if (not revisao or revisao.get("proposta_assinatura") != assinatura
            or revisao.get("hoje") != str(hoje)):
        return _nova_revisao(estado, prefixo, assinatura, hoje)
    return revisao


def _consultar(estado, proposta, prefixo, carregar_historico, hoje):
    revisao = _contexto(estado, proposta, prefixo, hoje)
    try:
        resultado = analisar_duplicidades(proposta, carregar_historico(), hoje)
        prova = assinatura_conferencia(proposta, resultado)
    except Exception:
        # Nova geração invalida a aprovação sem tocar na checkbox já renderizada.
        return _nova_revisao(
            estado, prefixo, revisao["proposta_assinatura"], hoje, erro=_READ_ERROR,
        )
    if revisao.get("prova") == prova and not revisao.get("erro"):
        # Contagens de registros alheios podem mudar sem alterar os candidatos.
        revisao["resultado"] = deepcopy(resultado)
        return revisao
    return _nova_revisao(
        estado, prefixo, revisao["proposta_assinatura"], hoje,
        resultado=resultado, prova=prova,
    )


def _registrar_confirmacao(estado, prefixo, geracao, widget_key):
    revisao = estado.get(_chave(prefixo))
    if revisao and revisao.get("geracao") == geracao:
        revisao["confirmada"] = estado.get(widget_key) is True


def limpar_conferencia(estado, prefixo):
    """Descarta apenas a prova desta área, depois de salvar ou trocar trabalho.

    O contador não volta a zero: widgets de uma conferência anterior não podem
    reaparecer marcados. Nenhum valor de widget já criado é alterado aqui.
    """
    estado.pop(_chave(prefixo), None)


def validar_salvamento(ui, proposta, *, prefixo, carregar_historico, hoje):
    """Reconsulta sempre. False pede que o chamador redesenhe a conferência.

    Esta função não executa rerun, nem persiste a proposta. O chamador mantém o
    rascunho, faz o rerun apropriado e limpa a conferência só após salvar de fato.
    """
    revisao = _consultar(ui.session_state, proposta, prefixo, carregar_historico, hoje)
    if revisao.get("erro"):
        return False
    candidatos = (revisao.get("resultado") or {}).get("candidatos", [])
    return not candidatos or revisao.get("confirmada") is True


def renderizar_conferencia(ui, proposta, *, prefixo, carregar_historico, hoje, abrir_proposta=None):
    """Mostra evidência somente leitura e registra a escolha do operador.

    ``abrir_proposta(numero)`` deve apenas navegar para consulta no Histórico,
    preservando o rascunho atual. Permissões são verificadas pelo integrador.
    """
    estado = ui.session_state
    revisao = _contexto(estado, proposta, prefixo, hoje)
    anterior = revisao.get("resultado") or {}
    abrir_area = bool(revisao.get("erro") or anterior.get("candidatos"))
    with ui.expander("🔎 Conferência de propostas semelhantes", expanded=abrir_area):
        ui.caption(
            "Consulta as propostas dos últimos 30 dias. Uma semelhança é um indício: "
            "o mesmo cliente pode fazer uma nova encomenda. Nenhuma proposta é alterada automaticamente."
        )
        if ui.button("Conferir propostas semelhantes", key=f"{prefixo}_consultar_duplicidades", width="stretch"):
            revisao = _consultar(estado, proposta, prefixo, carregar_historico, hoje)
        if revisao.get("erro"):
            ui.error(revisao["erro"])
            return
        resultado = revisao.get("resultado")
        if resultado is None:
            ui.caption("A conferência também acontece ao salvar uma nova proposta.")
            return

        for aviso in resultado.get("avisos", []):
            ui.caption(str(aviso))
        candidatos = resultado.get("candidatos", [])
        if not candidatos:
            ui.success("Nenhuma proposta semelhante foi encontrada nesta janela de comparação.")
            ui.caption("Antes de salvar, o Histórico será consultado novamente.")
            return

        ui.warning(
            f"Há {len(candidatos)} proposta(s) semelhante(s). Confira os registros abaixo "
            "antes de criar uma nova proposta."
        )
        rows = [{
            "Proposta": str(c.get("numero") or "Sem número"),
            "Data": str(c.get("data") or ""),
            "Cliente": str(c.get("cliente") or ""),
            "Situação": str(c.get("status") or ""),
            "Motivos": " · ".join(str(m) for m in c.get("motivos", [])),
            "Itens": str(c.get("resumo") or ""),
        } for c in candidatos]
        ui.dataframe(rows, hide_index=True, width="stretch")
        ui.caption("Todos os registros encontrados estão na tabela. Compare também a personalização e a situação no Histórico.")

        geracao = revisao["geracao"]
        widgets = f"{prefixo}_duplicidades_{geracao}"
        consultaveis = [c for c in candidatos if str(c.get("numero") or "").strip()]
        if abrir_proposta is not None and consultaveis:
            selecionado = ui.selectbox(
                "Proposta para consultar", list(range(len(consultaveis))),
                format_func=lambda i: (
                    f"{consultaveis[i]['numero']} · {consultaveis[i].get('data', '')} · "
                    f"{consultaveis[i].get('cliente', '')}"
                ),
                key=f"{widgets}_proposta",
            )
            if ui.button("Consultar no Histórico", key=f"{widgets}_abrir", width="stretch"):
                abrir_proposta(str(consultaveis[selecionado]["numero"]))

        confirm_key = f"{widgets}_confirmar"
        revisao["confirmada"] = ui.checkbox(
            "Conferi as propostas relacionadas e quero criar uma nova",
            value=bool(revisao.get("confirmada")), key=confirm_key,
            on_change=_registrar_confirmacao,
            args=(estado, prefixo, geracao, confirm_key),
        )
        ui.caption("Depois da conferência, use o botão normal de salvar. Alterar os dados ou os registros relacionados exige uma nova conferência.")
