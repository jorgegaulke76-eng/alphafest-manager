"""HF72: roteiro diario de conferencias sem escrita ou agenda automatica."""
from __future__ import annotations
from typing import Any


def roteiro_diario_hf72(resumo: dict[str, Any] | None) -> list[dict[str, str | int]]:
    """Ordena somente tarefas agregadas ja existentes no resumo HF71.

    Nunca converte pendencia em lead e nao afirma que tarefa foi realizada.
    """
    r = resumo if isinstance(resumo, dict) else {}

    def contagem(campo: str) -> int:
        try:
            valor = int(r.get(campo) or 0)
        except (TypeError, ValueError, OverflowError):
            return 0
        return max(0, valor)

    etapas = [
        ("1", "Conferir dados cadastrais", "conferencias",
         "Verificar IDs e vinculos no Historico antes de atribuir origem. Nao corrigir por telefone."),
        ("2", "Conferir registro de envio", "sem_registro_envio",
         "Abrir a conversa original e registrar envio somente se ele realmente ocorreu."),
        ("3", "Revisar retornos urgentes", "urgentes",
         "Conferir propostas elegiveis urgentes no painel de retornos; decidir contato manualmente."),
        ("4", "Revisar retornos de prioridade alta", "altos",
         "Conferir propostas elegiveis de prioridade alta, sem assumir falta de resposta."),
        ("5", "Revisar demais retornos", "normais",
         "Conferir propostas elegiveis normais; respeitar o contexto da conversa."),
    ]
    saida = []
    for ordem, titulo, chave, orientacao in etapas:
        qtd = contagem(chave)
        if qtd:
            saida.append({"Ordem": ordem, "Atividade": titulo,
                          "Registros para conferir": qtd, "Orientacao": orientacao})
    return saida


def texto_roteiro_hf72(roteiro: list[dict[str, Any]] | None, data: str) -> str:
    """Exporta apenas contagens e instrucoes fixas, sem IDs ou dados pessoais."""
    linhas = ["ALPHAFEST | ROTEIRO DIARIO DE CONFERENCIA",
              "Data de referencia: " + str(data or "Nao informada"), ""]
    if not roteiro:
        linhas.append("Sem tarefas sinalizadas nas categorias verificadas.")
    for item in roteiro or []:
        linhas.append(
            str(item.get("Ordem") or "") + ". " +
            str(item.get("Atividade") or "Conferencia") + ": " +
            str(item.get("Registros para conferir") or 0)
        )
    linhas.extend(["", "A lista nao comprova envio, venda ou ausencia de resposta.",
                   "Nenhum contato e feito e nenhuma tarefa e marcada automaticamente."])
    return "\n".join(linhas) + "\n"
