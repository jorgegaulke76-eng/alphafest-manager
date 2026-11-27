"""HF67 - orientacoes organicas baseadas em evidencias do painel HF66.

Modulo puro, somente leitura; nao publica conteudo nem altera campanhas.
Um canal com poucos registros nao e declarado vencedor.
"""
from __future__ import annotations

from typing import Any


def sugerir_acoes_organicas(relatorio: dict[str, Any] | None) -> dict[str, Any]:
    dados = relatorio or {}
    indicadores = dados.get("indicadores") or {}
    diagnostico = dados.get("diagnostico") or {}
    canais = dados.get("por_canal") or []
    produtos = dados.get("por_produto") or []

    total = max(0, int(indicadores.get("pedidos_aprovados") or 0))
    atribuidos = max(0, int(indicadores.get("pedidos_atribuidos") or 0))
    cobertura = (atribuidos / total) if total else None
    problemas = int(diagnostico.get("ids_atendimento_repetidos") or 0) + int(diagnostico.get("numeros_repetidos") or 0)
    acoes = []
    if total == 0:
        acoes.append({
            "tipo": "dados", "titulo": "Comece pelas vendas confirmadas",
            "descricao": "Ainda não há propostas aprovadas identificadas no histórico. Registre aprovações reais e mantenha os atendimentos vinculados antes de comparar canais.",
        })
    elif problemas:
        acoes.append({
            "tipo": "dados", "titulo": "Revise identificadores duplicados",
            "descricao": "Foram encontrados IDs ou números de proposta repetidos. Revise os registros antes de tomar decisões com base nos rankings.",
        })
    if total and (cobertura is None or cobertura < 0.7):
        acoes.append({
            "tipo": "dados", "titulo": "Melhore a identificação da origem das vendas",
            "descricao": f"Apenas {atribuidos} de {total} pedidos aprovados têm atendimento vinculado ({cobertura:.0%}). Registre a origem verdadeira nos próximos atendimentos; não atribua vendas antigas a um canal por suposição.",
        })

    # Para evidencias comerciais por canal, exija universo minimamente util e
    # cobertura de atribuicao. Isso nao demonstra causalidade ou retorno financeiro.
    confiavel = total > 0 and cobertura is not None and cobertura >= 0.7 and not problemas
    elegiveis = [
        c for c in canais
        if int(c.get("Atendimentos") or 0) >= 20
        and int(c.get("Atendimentos convertidos") or 0) >= 3
        and int(c.get("Pedidos aprovados") or 0) >= 3
        and str(c.get("Canal de origem") or "").strip().casefold() not in {"não informado", "nao informado", "outro"}
    ]
    if confiavel and elegiveis:
        melhor = sorted(elegiveis, key=lambda c: (
            -int(c.get("Atendimentos convertidos") or 0),
            -int(c.get("Pedidos aprovados") or 0),
            str(c.get("Canal de origem") or ""),
        ))[0]
        nome = str(melhor.get("Canal de origem") or "")
        acoes.append({
            "tipo": "canal", "titulo": f"Teste conteúdo orgânico em {nome}",
            "descricao": f"Entre os canais com pelo menos 20 atendimentos e 3 conversões, {nome} registra {int(melhor['Atendimentos convertidos'])} atendimentos convertidos. Faça um teste orgânico pequeno e acompanhe novos atendimentos; isso não comprova que o canal gera mais lucro.",
        })
    elif total:
        acoes.append({
            "tipo": "amostra", "titulo": "Ainda não há base para priorizar um canal",
            "descricao": "Para destacar um canal, são necessários ao menos 20 atendimentos, 3 atendimentos convertidos, 3 pedidos aprovados, 70% de atribuição geral e ausência de duplicatas. Continue registrando a origem real dos clientes.",
        })
    produtos_elegiveis = [
        p for p in produtos
        if int(p.get("Pedidos aprovados") or 0) >= 3
        and str(p.get("Produto") or "").strip().casefold() not in {"produto não identificado", "produto nao identificado"}
    ]
    if produtos_elegiveis:
        produto = sorted(produtos_elegiveis, key=lambda p: (
            -int(p.get("Pedidos aprovados") or 0),
            str(p.get("Produto") or ""),
        ))[0]
        acoes.append({
            "tipo": "produto", "titulo": f"Teste mostrar mais exemplos de {produto['Produto']}",
            "descricao": f"Esse produto aparece em {int(produto['Pedidos aprovados'])} pedidos aprovados. Considere um post orgânico com exemplos reais autorizados e acompanhe os pedidos futuros; não há medição de margem, causalidade ou lucro neste painel.",
        })
    elif total:
        acoes.append({
            "tipo": "produto_amostra", "titulo": "Sem produto destaque com amostra mínima",
            "descricao": "Ainda não há um produto identificado presente em pelo menos 3 pedidos aprovados. Continue registrando os itens sem criar campanhas baseadas em um pedido isolado.",
        })
    return {
        "cobertura_atribuicao": round(cobertura * 100, 1) if cobertura is not None else None,
        "amostra_canais_suficiente": confiavel and bool(elegiveis),
        "acoes": acoes,
        "observacao": "Sugestões para testes orgânicos, não previsão de vendas. Nenhuma publicação, cobrança ou gasto é realizado.",
    }
