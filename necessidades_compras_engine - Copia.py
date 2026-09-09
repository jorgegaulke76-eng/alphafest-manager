"""Motor puro da I8.12.5 — Central de Necessidades de Compras.

A central é derivada das faltas não cobertas por reserva/consumo da I8.13.2. Não cria
uma segunda fonte de pedidos, estoque, fornecedores ou custos. Este módulo
apenas agrega pendências por material para que todas as telas possam consumir
o mesmo resultado.
"""
from __future__ import annotations

from typing import Any, Iterable
from datetime import datetime

from consumo_estoque_engine import resumo_consumo


def _num(valor: Any) -> float:
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


def agregar_necessidades_compra(
    consumos: Iterable[dict],
    movimentos: Iterable[dict],
    propostas: Iterable[dict] | None = None,
) -> list[dict]:
    """Agrupa faltas confirmadas por material.

    Cada linha retorna somente fatos derivados das fontes oficiais existentes:
    quantidade pendente total e pedidos que compõem essa falta. Fornecedor e
    custo são enriquecidos pelo app a partir do histórico oficial de compras.
    """
    mapa_propostas = {
        str((p or {}).get("numero_proposta") or "").strip(): p
        for p in (propostas or [])
        if isinstance(p, dict) and str((p or {}).get("numero_proposta") or "").strip()
    }
    agregadas: dict[str, dict] = {}
    for consumo in (consumos or []):
        if not isinstance(consumo, dict) or consumo.get("estornado"):
            continue
        numero = str(consumo.get("numero_proposta") or "").strip()
        proposta = mapa_propostas.get(numero, {})
        resumo = resumo_consumo(consumo, movimentos or [])
        for nec in resumo.get("necessidades") or []:
            pendente = max(0.0, _num((nec or {}).get("pendente")))
            if pendente <= 1e-7:
                continue
            material_id = str((nec or {}).get("material_id") or "").strip()
            if not material_id:
                continue
            linha = agregadas.setdefault(material_id, {
                "material_id": material_id,
                "material_nome": str((nec or {}).get("material_nome") or "Material"),
                "unidade": str((nec or {}).get("unidade") or ""),
                "quantidade_pendente": 0.0,
                "pedidos": [],
                "produtos": [],
            })
            linha["quantidade_pendente"] = round(_num(linha.get("quantidade_pendente")) + pendente, 6)

            produtos = []
            for origem in (nec or {}).get("origens") or []:
                nome_prod = str((origem or {}).get("produto") or "").strip()
                if nome_prod and nome_prod not in produtos:
                    produtos.append(nome_prod)
                if nome_prod and nome_prod not in linha["produtos"]:
                    linha["produtos"].append(nome_prod)

            linha["pedidos"].append({
                "numero_proposta": numero,
                "cliente_nome": str(proposta.get("cliente_nome") or consumo.get("cliente_nome") or "Cliente"),
                "data_entrega": str(proposta.get("data_entrega") or ""),
                "quantidade_pendente": round(pendente, 6),
                "confirmado_em": str(consumo.get("confirmado_em") or ""),
                "produtos": produtos,
            })

    def _ordem_entrega(valor: Any) -> tuple:
        texto = str(valor or "").strip()
        for formato in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                data = datetime.strptime(texto[:10], formato).date()
                return (data.year, data.month, data.day)
            except Exception:
                pass
        return (9999, 12, 31)

    resultado = list(agregadas.values())
    for linha in resultado:
        linha["pedidos"].sort(key=lambda p: (_ordem_entrega(p.get("data_entrega")), str(p.get("confirmado_em") or ""), str(p.get("numero_proposta") or "")))
        linha["quantidade_pedidos"] = len(linha["pedidos"])
    resultado.sort(key=lambda x: (str(x.get("material_nome") or "").casefold(), str(x.get("material_id") or "")))
    return resultado
