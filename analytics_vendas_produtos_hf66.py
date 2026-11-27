"""HF66 - painel de conversao real por canal e produtos aprovados.

Servico somente leitura. Nunca associa cliente por nome/telefone, nao altera o
Historico e nao considera orcamento enviado como venda.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
from typing import Any

from proposal_status import proposta_encerrada, status_bool

ZERO = Decimal("0")
CENTAVOS = Decimal("0.01")
SEM_ORIGEM = "Não informado"
SEM_PRODUTO = "Produto não identificado"


def _dinheiro(valor: Any) -> Decimal | None:
    """Numero/BRL com virgula, rejeitando ausentes, negativos e nao finitos."""
    if valor is None or isinstance(valor, bool):
        return None
    texto = str(valor).strip().replace("R$", "").replace("\xa0", "").replace(" ", "")
    if not texto:
        return None
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    if not re.fullmatch(r"[+]?(?:\d+(?:\.\d+)?|\.\d+)", texto):
        return None
    try:
        d = Decimal(texto)
        return d if d.is_finite() and d >= ZERO else None
    except InvalidOperation:
        return None


def _quantidade(valor: Any) -> Decimal | None:
    d = _dinheiro(valor)
    return d if d is not None and d > ZERO else None


def _valor_aprovado(proposta: dict[str, Any]) -> Decimal | None:
    """Valor total do pedido aprovado, com desconto/frete apenas no fallback."""
    for chave in ("valor_total", "total", "total_geral"):
        if chave in proposta and proposta[chave] not in (None, ""):
            return _dinheiro(proposta[chave])
    itens = proposta.get("itens")
    if not isinstance(itens, list) or not itens:
        return None
    subtotal = ZERO
    for item in itens:
        if not isinstance(item, dict):
            return None
        qtd = _quantidade(item.get("quantidade"))
        unitario = _dinheiro(item.get("valor_unitario"))
        if qtd is None or unitario is None:
            return None
        subtotal += qtd * unitario
    desconto = _dinheiro(proposta.get("desconto", proposta.get("desconto_valor", 0)))
    taxa = _dinheiro(proposta.get("taxa_entrega", 0))
    if desconto is None or taxa is None:
        return None
    return max(subtotal - desconto, ZERO) + taxa


def _canal(atendimento: dict[str, Any]) -> str:
    for campo in ("canal_origem", "origem", "canal"):
        texto = " ".join(str(atendimento.get(campo) or "").split())
        if texto and texto.casefold() not in {"não informado", "nao informado", "nenhum", "none", "outro não informado"}:
            return texto
    return SEM_ORIGEM


def _nome_produto(item: dict[str, Any]) -> str:
    for campo in ("produto", "nome"):
        nome = " ".join(str(item.get(campo) or "").split())
        if nome:
            return nome
    return SEM_PRODUTO


def consolidar_vendas_e_produtos(atendimentos: list[dict[str, Any]] | None,
                                historico: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Vendas: so propostas aprovadas e nao encerradas. Canal: vinculo ID explicito.

    Produtos: todo Historico aprovado, mesmo orcamento legado sem atendimento.
    Valor bruto do item nao e o valor liquido da proposta ou receita recebida.
    """
    contatos: dict[str, dict[str, Any]] = {}
    problemas = {
        "contatos_sem_id": 0, "ids_atendimento_repetidos": 0,
        "propostas_sem_numero": 0, "numeros_repetidos": 0,
        "aprovadas_sem_atendimento": 0, "aprovadas_vinculo_invalido": 0,
        "pedidos_sem_total_confiavel": 0, "itens_sem_valor_unitario": 0,
    }
    for item in atendimentos or []:
        if not isinstance(item, dict):
            continue
        aid = str(item.get("id") or "").strip()
        if not aid:
            problemas["contatos_sem_id"] += 1
            continue
        if aid in contatos:
            problemas["ids_atendimento_repetidos"] += 1
            continue
        contatos[aid] = item

    grupos: dict[str, dict[str, Any]] = {}
    for aid, item in contatos.items():
        nome = _canal(item)
        grupo = grupos.setdefault(nome, {
            "canal": nome, "contatos": 0, "convertidos_ids": set(),
            "pedidos_aprovados": 0, "valor_aprovado": ZERO,
        })
        grupo["contatos"] += 1

    produtos: dict[str, dict[str, Any]] = {}
    aprovadas = 0
    valor_geral = ZERO
    pedidos_atribuidos = 0
    numeros = set()
    for proposta in historico or []:
        if not isinstance(proposta, dict):
            continue
        numero = str(proposta.get("numero_proposta") or "").strip()
        if not numero:
            problemas["propostas_sem_numero"] += 1
            continue
        if numero in numeros:
            problemas["numeros_repetidos"] += 1
            continue
        numeros.add(numero)
        if not status_bool(proposta, "aprovado") or proposta_encerrada(proposta):
            continue

        aprovadas += 1
        total = _valor_aprovado(proposta)
        if total is None:
            problemas["pedidos_sem_total_confiavel"] += 1
        else:
            valor_geral += total

        aid = str(proposta.get("atendimento_id") or "").strip()
        if not aid:
            problemas["aprovadas_sem_atendimento"] += 1
        elif aid not in contatos:
            problemas["aprovadas_vinculo_invalido"] += 1
        else:
            pedidos_atribuidos += 1
            grupo = grupos[_canal(contatos[aid])]
            grupo["convertidos_ids"].add(aid)
            grupo["pedidos_aprovados"] += 1
            if total is not None:
                grupo["valor_aprovado"] += total

        itens = proposta.get("itens") or []
        if not isinstance(itens, list):
            continue
        for item in itens:
            if not isinstance(item, dict):
                continue
            nome = _nome_produto(item)
            chave = nome.casefold()
            prod = produtos.setdefault(chave, {
                "nome": nome, "pedidos_ids": set(), "quantidade": ZERO,
                "valor_bruto": ZERO,
            })
            prod["pedidos_ids"].add(numero)
            qtd = _quantidade(item.get("quantidade"))
            preco = _dinheiro(item.get("valor_unitario"))
            if qtd is not None:
                prod["quantidade"] += qtd
            if qtd is None or preco is None:
                problemas["itens_sem_valor_unitario"] += 1
            else:
                prod["valor_bruto"] += qtd * preco

    canais = []
    for grupo in grupos.values():
        contatos_canal = grupo["contatos"]
        convertidos = len(grupo["convertidos_ids"])
        canais.append({
            "Canal de origem": grupo["canal"],
            "Atendimentos": contatos_canal,
            "Atendimentos convertidos": convertidos,
            "Pedidos aprovados": grupo["pedidos_aprovados"],
            "Conversão (%)": round(100 * convertidos / contatos_canal, 1) if contatos_canal else 0.0,
            "Valor aprovado (R$)": float(grupo["valor_aprovado"].quantize(CENTAVOS, rounding=ROUND_HALF_UP)),
        })
    canais.sort(key=lambda x: (-x["Pedidos aprovados"], -x["Atendimentos convertidos"], x["Canal de origem"]))
    produtos_saida = []
    for prod in produtos.values():
        produtos_saida.append({
            "Produto": prod["nome"],
            "Pedidos aprovados": len(prod["pedidos_ids"]),
            "Quantidade": float(prod["quantidade"]),
            "Bruto dos itens (R$)": float(prod["valor_bruto"].quantize(CENTAVOS, rounding=ROUND_HALF_UP)),
        })
    produtos_saida.sort(key=lambda x: (-x["Pedidos aprovados"], -x["Bruto dos itens (R$)"], x["Produto"]))
    total_atendimentos = len(contatos)
    convertidos_total = len({aid for g in grupos.values() for aid in g["convertidos_ids"]})
    return {
        "indicadores": {
            "atendimentos": total_atendimentos,
            "atendimentos_convertidos": convertidos_total,
            "taxa_conversao": round(100 * convertidos_total / total_atendimentos, 1) if total_atendimentos else 0.0,
            "pedidos_aprovados": aprovadas,
            "pedidos_atribuidos": pedidos_atribuidos,
            "valor_aprovado": float(valor_geral.quantize(CENTAVOS, rounding=ROUND_HALF_UP)),
        },
        "por_canal": canais,
        "por_produto": produtos_saida,
        "diagnostico": problemas,
    }
