"""Regras puras de materiais por pedido — AlphaFest Manager I8.13.5-HF4.

Este módulo não acessa Streamlit, Supabase ou arquivos. Ele concentra decisões já
homologadas de reserva/consumo para que a UI apenas carregue, persista e audite.

Regras centrais preservadas:
- Ficha Técnica é opcional por pedido;
- modos: ficha padrão, materiais manuais ou sem consumo controlado;
- confirmar materiais cria reserva/necessidade, nunca baixa física;
- baixa física só ocorre no início real da produção;
- Entregue/Pronto não entram na fila de liberação de materiais.
"""
from __future__ import annotations

import hashlib
import json
from typing import Callable, Iterable, Optional

EPS = 0.0000001
MODOS_CONSUMO = {"ficha_padrao", "manual_pedido", "sem_consumo"}


def _num(valor, padrao: float = 0.0) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return float(padrao)


def normalizar_modo_consumo(modo_consumo) -> str:
    modo = str(modo_consumo or "ficha_padrao").strip().casefold()
    aliases = {
        "ficha": "ficha_padrao",
        "ficha_padrao": "ficha_padrao",
        "ficha padrão": "ficha_padrao",
        "manual": "manual_pedido",
        "manual_pedido": "manual_pedido",
        "materiais_pedido": "manual_pedido",
        "sem_consumo": "sem_consumo",
        "sem consumo": "sem_consumo",
        "nenhum": "sem_consumo",
    }
    return aliases.get(modo, modo)


def consumo_ativo_pedido(numero_proposta, consumos: Iterable[dict]) -> Optional[dict]:
    numero = str(numero_proposta or "").strip()
    candidatos = [
        c for c in (consumos or [])
        if isinstance(c, dict)
        and str(c.get("numero_proposta") or "").strip() == numero
        and not c.get("estornado")
    ]
    if not candidatos:
        return None
    candidatos.sort(
        key=lambda c: (str(c.get("confirmado_em") or ""), str(c.get("id") or "")),
        reverse=True,
    )
    return candidatos[0]


def proposta_na_fila_liberacao(
    proposta: dict,
    *,
    numeros_consumo_ativos: Optional[Iterable[str]] = None,
    aprovado: bool = False,
    pronto: bool = False,
    entregue: bool = False,
) -> bool:
    """Decide apenas se o pedido deve aparecer na fila de liberação de materiais."""
    proposta = proposta or {}
    numero = str(proposta.get("numero_proposta") or "").strip()
    if not numero or not aprovado or pronto or entregue:
        return False
    ativos = {str(x or "").strip() for x in (numeros_consumo_ativos or [])}
    return numero not in ativos


def assinatura_previa(produtos, necessidades, normalizar_produto: Callable[[object], str]) -> str:
    payload = {
        "produtos": sorted([
            {
                "produto": normalizar_produto((x or {}).get("produto")),
                "quantidade": round(_num((x or {}).get("quantidade")), 6),
                "ficha_id": str((x or {}).get("ficha_id") or ""),
            }
            for x in (produtos or []) if isinstance(x, dict)
        ], key=lambda x: (x["produto"], x["ficha_id"], x["quantidade"])),
        "necessidades": sorted([
            {
                "material_id": str((x or {}).get("material_id") or ""),
                "necessario": round(_num((x or {}).get("necessario")), 6),
            }
            for x in (necessidades or []) if isinstance(x, dict)
        ], key=lambda x: x["material_id"]),
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _snapshot_produtos_basico(proposta: dict) -> list[dict]:
    produtos = []
    for item in (proposta or {}).get("itens") or []:
        if not isinstance(item, dict):
            continue
        nome = str(item.get("produto") or "").strip()
        qtd = max(0.0, _num(item.get("quantidade", 0)))
        if nome and qtd > 0:
            produtos.append({"produto": nome, "quantidade": qtd, "ficha_id": ""})
    return produtos


def _necessidades_manuais(estoque: dict, linhas) -> list[dict]:
    materiais = {
        str((m or {}).get("id") or ""): m
        for m in (estoque or {}).get("materiais") or []
        if isinstance(m, dict)
    }
    agregadas: dict[str, dict] = {}
    for linha in linhas or []:
        if not isinstance(linha, dict):
            continue
        material_id = str(linha.get("material_id") or "").strip()
        qtd = max(0.0, _num(linha.get("necessario", linha.get("quantidade", 0))))
        material = materiais.get(material_id)
        if not material or not material.get("ativo", True) or qtd <= EPS:
            continue
        destino = agregadas.setdefault(material_id, {
            "material_id": material_id,
            "material_nome": str(material.get("nome") or "Material"),
            "unidade": str(material.get("unidade") or ""),
            "necessario": 0.0,
            "origens": [],
        })
        destino["necessario"] = round(_num(destino.get("necessario")) + qtd, 6)
        destino["origens"].append({
            "produto": "Definição manual deste pedido",
            "necessario": qtd,
        })
    return sorted(agregadas.values(), key=lambda x: str(x.get("material_nome") or "").casefold())


def preparar_confirmacao_consumo(
    *,
    proposta: dict,
    previa: dict,
    estoque: dict,
    modo_consumo="ficha_padrao",
    necessidades_manuais=None,
    aceitar_sem_ficha: bool = False,
    aprovado: bool = False,
    ja_possui_consumo_ativo: bool = False,
    usuario_nome: str = "Jorge",
    agora_iso: str,
    consumo_id: str,
    normalizar_produto: Callable[[object], str],
) -> dict:
    """Valida e monta o documento de consumo sem persistir nada."""
    proposta = proposta or {}
    previa = previa or {}
    numero = str(proposta.get("numero_proposta") or "").strip()
    if not numero:
        return {"ok": False, "mensagem": "Proposta inválida.", "consumo": None}
    if not aprovado:
        return {
            "ok": False,
            "mensagem": "A necessidade de materiais só pode ser confirmada depois que o pedido estiver aprovado.",
            "consumo": None,
        }
    if ja_possui_consumo_ativo:
        return {
            "ok": False,
            "mensagem": "Este pedido já possui reserva/consumo ativo. Estorne a liberação atual antes de confirmar novamente.",
            "consumo": None,
        }
    if previa.get("sem_catalogo"):
        return {
            "ok": False,
            "mensagem": "Há item(ns) sem vínculo seguro com o Catálogo Oficial. Resolva o vínculo antes de liberar este pedido.",
            "consumo": None,
        }

    modo = normalizar_modo_consumo(modo_consumo)
    if modo not in MODOS_CONSUMO:
        return {"ok": False, "mensagem": "Escolha como tratar o consumo de estoque deste pedido.", "consumo": None}

    produtos_snapshot = _snapshot_produtos_basico(proposta)
    necessidades: list[dict] = []

    if modo == "ficha_padrao":
        if previa.get("sem_ficha") and not aceitar_sem_ficha:
            return {
                "ok": False,
                "mensagem": "Há item(ns) sem Ficha Técnica. Escolha materiais específicos deste pedido ou confirme que ele não consome estoque controlado.",
                "consumo": None,
            }
        necessidades = [dict(x) for x in (previa.get("necessidades") or []) if isinstance(x, dict)]
        if not necessidades:
            return {
                "ok": False,
                "mensagem": "Nenhuma Ficha Técnica com material controlado foi encontrada. Escolha materiais deste pedido ou 'Sem consumo de estoque controlado'.",
                "consumo": None,
            }
        produtos_snapshot = [dict(x) for x in (previa.get("produtos") or []) if isinstance(x, dict)] or produtos_snapshot

    elif modo == "manual_pedido":
        necessidades = _necessidades_manuais(estoque, necessidades_manuais)
        if not necessidades:
            return {
                "ok": False,
                "mensagem": "Selecione pelo menos um material e informe uma quantidade maior que zero.",
                "consumo": None,
            }

    detalhe_modo = {
        "ficha_padrao": "Ficha Técnica padrão confirmada para reserva",
        "manual_pedido": "Materiais definidos especificamente para este pedido",
        "sem_consumo": "Pedido confirmado sem consumo de estoque controlado",
    }[modo]
    modelo = {
        "ficha_padrao": "reserva_consumo_real_v1",
        "manual_pedido": "materiais_pedido_v1",
        "sem_consumo": "sem_consumo_controlado_v1",
    }[modo]

    consumo = {
        "id": str(consumo_id or ""),
        "numero_proposta": numero,
        "cliente_nome": str(proposta.get("cliente_nome") or ""),
        "produtos": produtos_snapshot,
        "necessidades": necessidades,
        "itens_sem_ficha_confirmados": previa.get("sem_ficha") or [],
        "itens_sem_catalogo_confirmados": previa.get("sem_catalogo") or [],
        "itens_materiais_estoque_reconhecidos": previa.get("materiais_estoque_pedido") or [],
        "assinatura_confirmada": assinatura_previa(produtos_snapshot, necessidades, normalizar_produto),
        "modo_consumo": modo,
        "modo_consumo_descricao": detalhe_modo,
        "confirmado_em": str(agora_iso or ""),
        "confirmado_por": str(usuario_nome or "Jorge") or "Jorge",
        "atualizado_em": str(agora_iso or ""),
        "estornado": False,
        "modelo_materiais": modelo,
        "reservas": [],
        "eventos": [{
            "em": str(agora_iso or ""),
            "usuario": str(usuario_nome or "Jorge") or "Jorge",
            "tipo": "confirmacao",
            "detalhe": detalhe_modo,
        }],
    }
    return {
        "ok": True,
        "mensagem": "",
        "consumo": consumo,
        "modo": modo,
        "detalhe_modo": detalhe_modo,
        "necessidades": necessidades,
        "produtos_snapshot": produtos_snapshot,
    }


def decidir_inicio_consumo(consumo: dict, resumo: dict) -> dict:
    """Decide se iniciar produção deve criar baixa física, sem persistir nada."""
    consumo = consumo or {}
    resumo = resumo or {}
    pendentes = [
        n for n in (resumo.get("necessidades") or [])
        if isinstance(n, dict) and _num(n.get("pendente")) > EPS
    ]
    if pendentes:
        nomes = ", ".join(str(n.get("material_nome") or "Material") for n in pendentes[:3])
        return {
            "ok": False,
            "mensagem": f"Ainda há material sem reserva ({nomes}). Receba/compre o faltante antes de iniciar a produção.",
            "necessidades": [],
        }
    if str(consumo.get("modo_consumo") or "") == "sem_consumo":
        return {
            "ok": True,
            "mensagem": "Pedido sem consumo de estoque controlado; nenhuma baixa física necessária.",
            "necessidades": [],
        }
    a_consumir = [
        dict(n) for n in (resumo.get("necessidades") or [])
        if isinstance(n, dict) and _num(n.get("reservado")) > EPS
    ]
    if not a_consumir:
        return {
            "ok": True,
            "mensagem": "Materiais já estavam consumidos fisicamente; nenhuma nova baixa foi necessária.",
            "necessidades": [],
        }
    return {"ok": True, "mensagem": "", "necessidades": a_consumir}
