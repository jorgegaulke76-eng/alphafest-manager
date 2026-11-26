"""Resumo operacional diário, somente leitura, sem nomes ou contatos."""
from datetime import date, datetime

def montar_resumo_anna(dia, *, novos, aguardando, ativos, entregas):
    if isinstance(dia, datetime):
        dia = dia.date()
    if not isinstance(dia, date):
        raise TypeError("Data invalida")
    totais = (novos, aguardando, ativos, entregas)
    if any(type(v) is not int or v < 0 for v in totais):
        raise ValueError("Totais devem ser inteiros nao negativos")
    tarefas = []
    if entregas:
        tarefas.append("- Conferir entregas previstas para hoje")
    if novos:
        tarefas.append("- Atender novos contatos")
    if aguardando:
        tarefas.append("- Retomar contatos aguardando cliente")
    if not tarefas:
        tarefas.append("- Conferir agenda e demais etapas da operacao")
    return "\n".join([
        "ALPHAFEST | RESUMO DO DIA - " + dia.strftime("%d/%m/%Y"), "",
        f"Novos atendimentos: {novos}",
        f"Aguardando cliente: {aguardando}",
        f"Pedidos ativos: {ativos}",
        f"Entregas previstas hoje: {entregas}", "", "PRIORIDADES",
        *tarefas, "", "Conferir detalhes no Manager AlphaFest.", ""
    ])
