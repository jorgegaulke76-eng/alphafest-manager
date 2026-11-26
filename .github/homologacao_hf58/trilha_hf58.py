"""Registra transições da Caixa do Projeto somente na demonstração local.

Não é histórico oficial nem substitui conferência do cliente ou do Supabase.
"""
from __future__ import annotations

from datetime import datetime
from ficha_producao_hf58 import artes, situacao_arte


def adicionar_transicao(trilha, anterior, novo, *, passo, perfil, instante):
    """Registra apenas mudança efetiva de status após gravação aceita pela UI."""
    status_antigo, _ = situacao_arte(anterior)
    status_novo, _ = situacao_arte(novo)
    historico = list(trilha or [])
    if status_antigo == status_novo:
        return historico
    lista = artes(novo)
    arte = lista[-1] if lista else {}
    evento = {
        "Passo": int(passo),
        "Perfil": str(perfil)[:45],
        "Antes": status_antigo,
        "Depois": status_novo,
        "Arte": str(arte.get("nome") or "sem arte")[:160],
        "ID": str(arte.get("id") or "-")[:70],
        "Registrado": instante.strftime("%d/%m/%Y %H:%M:%S") if isinstance(instante, datetime) else "",
    }
    return (historico + [evento])[-50:]


def relatorio_trilha_txt(trilha):
    linhas = [
        "ALPHAFEST HF65.24.58 | TRILHA DE HOMOLOGACAO FICTICIA",
        "Registro local em memoria, NAO EVIDENCIA DE BANCO OU CLIENTE.",
        "",
    ]
    for item in trilha or []:
        linhas.append(
            f'Passo {item.get("Passo")}: {item.get("Antes")} -> {item.get("Depois")}'
            f' | Perfil: {item.get("Perfil")} | Arte: {item.get("Arte")}'
            f' | ID: {item.get("ID")} | {item.get("Registrado")}'
        )
    linhas.append("")
    linhas.append("Produção e aprovação comercial não são alteradas pelo simulador.")
    return ("\n".join(linhas) + "\n").encode("utf-8-sig")
