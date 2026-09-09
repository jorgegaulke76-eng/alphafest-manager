"""Alpha Marketing Autopilot — seleção segura de produtos para divulgação.

Fase 1: prioriza produtos do catálogo usando sinais já disponíveis no Manager
(métricas do site + qualidade mínima do cadastro). Não publica em redes.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).casefold()
    return re.sub(r"\s+", " ", text).strip()


def _names_from_rank(items: Any) -> dict[str, float]:
    result: dict[str, float] = {}
    if not isinstance(items, list):
        return result
    for idx, item in enumerate(items):
        if isinstance(item, dict):
            name = item.get("product_name") or item.get("produto") or item.get("name") or item.get("Nome") or ""
            count = item.get("count") or item.get("total") or item.get("value") or 0
        elif isinstance(item, (list, tuple)) and item:
            name = item[0]
            count = item[1] if len(item) > 1 else 0
        else:
            continue
        key = _norm(name)
        if key:
            try:
                value = float(count or 0)
            except Exception:
                value = 0.0
            # posição também vale como sinal, mesmo se o backend não entregar count.
            result[key] = max(value, float(max(1, 12 - idx)))
    return result


def rank_products(catalog: list[dict[str, Any]], metrics: dict[str, Any] | None = None, limit: int = 8) -> list[dict[str, Any]]:
    """Retorna produtos aptos para criação automática, com motivos auditáveis."""
    metrics = metrics or {}
    opens = _names_from_rank(metrics.get("top_products"))
    whatsapp = _names_from_rank(metrics.get("top_whatsapp_products"))
    ranked: list[dict[str, Any]] = []

    for product in catalog or []:
        if not isinstance(product, dict):
            continue
        name = str(product.get("Nome") or "").strip()
        if not name:
            continue
        images = product.get("Imagens") or []
        if isinstance(images, str):
            images = [images] if images.strip() else []
        images = [str(x).strip() for x in images if str(x).strip()]
        if not images:
            continue

        key = _norm(name)
        score = 30.0  # imagem + nome tornam o produto minimamente publicável
        reasons = ["foto disponível"]
        description = str(product.get("Descricao") or "").strip()
        category = str(product.get("Categoria") or "").strip()
        if description:
            score += 8
            reasons.append("descrição pronta")
        if category:
            score += 4
        if opens.get(key):
            score += min(25.0, opens[key] * 2.0)
            reasons.append("produto acessado no site")
        if whatsapp.get(key):
            score += min(35.0, whatsapp[key] * 4.0)
            reasons.append("gerou clique no WhatsApp")

        # Compatibilidade com campos recentes sem depender de um nome único.
        highlight = product.get("Destaque") or product.get("destaque") or product.get("SiteDestaque")
        if str(highlight).strip().casefold() in {"1", "true", "sim", "yes", "on"} or highlight is True:
            score += 12
            reasons.append("marcado como destaque")

        ranked.append({
            "product": product,
            "name": name,
            "image": images[0],
            "score": round(score, 1),
            "reasons": reasons,
        })

    ranked.sort(key=lambda item: (-item["score"], _norm(item["name"])))
    return ranked[: max(1, int(limit or 8))]
