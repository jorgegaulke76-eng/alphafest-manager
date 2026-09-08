"""HF53.2-HF5-HF3 — Designer Comercial Mestre AlphaFest.

Camada determinística de direção de arte e copy para o Piloto Automático.
Não publica nada e não depende de serviço externo. Seu papel é preparar textos
mais coerentes, evitar repetições, limitar carga visual e validar o pacote antes
de salvá-lo na Central de Campanhas.
"""
from __future__ import annotations

import io
import re
import unicodedata
from typing import Any

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

_CHANNEL_LIMITS = {
    "Instagram Feed": {"title": 34, "subtitle": 68, "description": 155},
    "Facebook": {"title": 38, "subtitle": 78, "description": 175},
    "Instagram Story": {"title": 30, "subtitle": 54, "description": 105},
    "Status WhatsApp": {"title": 30, "subtitle": 50, "description": 90},
}

_PROFILES = [
    (
        ("laser", "gravação", "gravacao"),
        {
            "subtitle": "Personalização durável para presentes, brindes e empresas",
            "benefits": [
                "Design exclusivo",
                "Fácil de usar",
                "Material de qualidade",
                "Personalizado sob medida",
                "Múltiplos usos",
            ],
            "cta": "CONHEÇA ESTE PRODUTO",
        },
    ),
    (
        ("caneca", "copo", "brinde"),
        {
            "subtitle": "Um presente útil com a sua identidade",
            "benefits": ["Personalização exclusiva", "Ideal para presentes e empresas", "Produção sob encomenda"],
            "cta": "FALE COM A ALPHAFEST",
        },
    ),
    (
        ("balão", "balao", "decoração", "decoracao"),
        {
            "subtitle": "Cores e detalhes para transformar sua comemoração",
            "benefits": ["Projeto personalizado", "Opções para diferentes ocasiões", "Atendimento sob medida"],
            "cta": "PEÇA SEU ORÇAMENTO",
        },
    ),
    (
        ("papel", "convite", "topo", "lembrança", "lembranca", "personalizado"),
        {
            "subtitle": "Detalhes personalizados para tornar a ocasião ainda mais especial",
            "benefits": ["Feito do seu jeito", "Produção sob medida", "Ideal para festas e presentes"],
            "cta": "FAÇA SEU PEDIDO",
        },
    ),
]

_DEFAULT = {
    "subtitle": "Personalizado do seu jeito, para sua festa, presente ou empresa",
    "benefits": ["Produção sob medida", "Atendimento personalizado", "Feito para a sua necessidade"],
    "cta": "FAÇA SEU PEDIDO",
}

_STOP_DUP = {"alphafest", "personalizado", "personalizada", "personalização", "personalizacao"}


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).casefold()
    return re.sub(r"\s+", " ", text).strip()


def _clean(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip(" \t\r\n-–—•;,.!")
    return text


def _clip(text: str, limit: int) -> str:
    text = _clean(text)
    if len(text) <= limit:
        return text
    cut = text[: max(1, limit - 1)].rsplit(" ", 1)[0].strip()
    return (cut or text[: max(1, limit - 1)]).rstrip(".,;:-") + "…"


def _profile(product: dict[str, Any]) -> dict[str, Any]:
    hay = _norm(" ".join(str(product.get(k) or "") for k in ("Nome", "Descricao", "Categoria", "Subcategoria")))
    for needles, data in _PROFILES:
        if any(_norm(n) in hay for n in needles):
            return data
    return _DEFAULT


def _dedupe_phrases(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: list[set[str]] = []
    for item in items:
        clean = _clean(item)
        if not clean:
            continue
        words = {w for w in re.findall(r"[a-z0-9á-ú]+", _norm(clean)) if len(w) > 3 and w not in _STOP_DUP}
        duplicate = False
        for old in seen:
            if words and old:
                overlap = len(words & old) / max(1, min(len(words), len(old)))
                if overlap >= 0.75:
                    duplicate = True
                    break
        if not duplicate:
            result.append(clean)
            seen.append(words)
    return result


def build_design_plan(product: dict[str, Any], objective: str = "Vender", campaign: str = "", channels: list[str] | None = None) -> dict[str, Any]:
    """Cria a direção comercial que será usada por todos os formatos."""
    channels = list(channels or [])
    profile = _profile(product)
    name = _clean(product.get("Nome")) or "Produto AlphaFest"
    desc = _clean(product.get("Descricao"))
    campaign = _clean(campaign)
    objective = _clean(objective) or "Vender"

    # HF53.2-HF5-HF3: a direção já nasce dentro das áreas seguras.
    # Antes o plano podia criar um benefício com 88 caracteres e a própria
    # revisão recusava qualquer benefício acima de 72.
    title = _clip(name.upper(), 52)
    subtitle = profile["subtitle"]
    if campaign and _norm(campaign) not in {"permanente", "campanha permanente"}:
        subtitle = f"{campaign}: {subtitle}"

    benefits = [_clip(x, 68) for x in _dedupe_phrases(list(profile["benefits"]))[:5]]
    if desc:
        first = re.split(r"(?<=[.!?])\s+", desc)[0]
        first = _clip(first, 68)
        if first and not any(_norm(first) == _norm(x) for x in benefits):
            benefits = [_clip(x, 68) for x in _dedupe_phrases([first] + benefits)[:5]]

    subtitle = _clip(subtitle, 120)
    description = " • ".join(benefits)
    cta = _clip(profile["cta"], 28)
    if _norm(objective) == "corporativo":
        subtitle = _clip("Sua marca em destaque com personalização sob medida", 120)
        cta = _clip("SOLICITE SEU ORÇAMENTO", 28)
    elif _norm(objective) in {"novidade", "apresentar produto"}:
        cta = _clip("CONHEÇA ESTE PRODUTO", 28)

    per_channel: dict[str, dict[str, str]] = {}
    for channel in channels:
        limits = _CHANNEL_LIMITS.get(channel, _CHANNEL_LIMITS["Instagram Feed"])
        per_channel[channel] = {
            "title": _clip(title, limits["title"]),
            "subtitle": _clip(subtitle, limits["subtitle"]),
            "description": _clip(description, limits["description"]),
            "cta": _clip(cta, 28).upper(),
        }

    return {
        "title": title,
        "subtitle": subtitle,
        "benefits": benefits,
        "description": description,
        "cta": cta,
        "objective": objective,
        "campaign": campaign or "Permanente",
        "channels": per_channel,
        "rules_version": "HF53.2-HF5-HF3",
    }


def sanitize_channel_copy(text: str, channel: str) -> str:
    """Remove repetições óbvias e limita excesso de linhas sem destruir hashtags."""
    raw_lines = [re.sub(r"\s+", " ", line).strip() for line in str(text or "").splitlines()]
    result: list[str] = []
    normalized_seen: set[str] = set()
    blank = False
    max_nonblank = 12 if channel in {"Instagram Feed", "Facebook"} else 8
    nonblank = 0
    for line in raw_lines:
        if not line:
            if result and not blank:
                result.append("")
            blank = True
            continue
        blank = False
        key = re.sub(r"[^a-z0-9]+", " ", _norm(line)).strip()
        if key and key in normalized_seen:
            continue
        if key:
            normalized_seen.add(key)
        nonblank += 1
        if nonblank > max_nonblank:
            continue
        result.append(line)
    return "\n".join(result).strip()


def validate_design_plan(plan: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    checks.append({"id": "title", "ok": bool(_clean(plan.get("title"))), "label": "Título presente"})
    checks.append({"id": "subtitle", "ok": bool(_clean(plan.get("subtitle"))), "label": "Subtítulo coerente"})
    benefits = list(plan.get("benefits") or [])
    checks.append({"id": "benefits", "ok": 3 <= len(benefits) <= 5, "label": "3 a 5 benefícios sem excesso"})
    checks.append({"id": "cta", "ok": bool(_clean(plan.get("cta"))), "label": "CTA presente"})
    checks.append({"id": "channels", "ok": bool(plan.get("channels")), "label": "Formatos definidos"})
    checks.append({"id": "title_length", "ok": len(_clean(plan.get("title"))) <= 52, "label": "Título dentro da área segura"})
    checks.append({"id": "subtitle_length", "ok": len(_clean(plan.get("subtitle"))) <= 120, "label": "Faixa de campanha sem excesso"})
    checks.append({"id": "benefit_length", "ok": all(len(_clean(x)) <= 72 for x in benefits), "label": "Benefícios compatíveis com o layout"})
    checks.append({"id": "cta_length", "ok": len(_clean(plan.get("cta"))) <= 28, "label": "CTA curto e dominante"})
    score = round(100 * sum(1 for x in checks if x["ok"]) / max(1, len(checks)))
    failed = [x["label"] for x in checks if not x["ok"]]
    return {"ok": not failed, "score": score, "checks": checks, "failed": failed}


def validate_art_bytes(data: bytes, expected_size: tuple[int, int]) -> dict[str, Any]:
    if not data or Image is None:
        return {"ok": False, "reason": "arquivo de arte inválido"}
    try:
        with Image.open(io.BytesIO(data)) as img:
            size = tuple(img.size)
            rgb = img.convert("RGB")
            extrema = rgb.getextrema()
            contrast = max((hi-lo) for lo,hi in extrema) if extrema else 0
            # Amostra simples para impedir arquivo vazio/quase uniforme.
            sample = rgb.resize((24,24))
            colors = sample.getcolors(maxcolors=24*24) or []
            diversity = len(colors)
            ok = size == tuple(expected_size) and img.width >= 1000 and img.height >= 1000 and contrast >= 35 and diversity >= 12
            reason = "ok" if ok else ("dimensão divergente" if size != tuple(expected_size) else "arte visualmente vazia ou sem contraste suficiente")
            return {"ok": ok, "size": size, "expected_size": tuple(expected_size), "contrast": contrast, "diversity": diversity, "reason": reason}
    except Exception:
        return {"ok": False, "reason": "PNG não pôde ser validado"}
