"""HF65.24.53 — proposta de vínculo auditável campanha ↔ pedido.

Funções puras, sem banco, sem Streamlit e sem confirmação automática de venda.
O atendente precisa selecionar uma proposta existente e confirmar a referência.
O histórico de alterações é append-only e inclui revogações.
"""
from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Iterable, Mapping

_CAMPAIGN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,119}$", re.ASCII)
_DECISIONS = {"confirmar", "revogar"}
_EVIDENCES = {"mensagem_whatsapp", "referencia_cliente", "link_utm_conferido", "atendimento_manual"}


def clean_campaign(raw: Any) -> str:
    value = str(raw or "").strip().lower()
    if not _CAMPAIGN.fullmatch(value) or re.search(r"\d{9,}", value):
        raise ValueError("Campanha inválida: use letras, números, _ ou -, sem dados pessoais.")
    return value


def build_attribution_event(
    *, numero_proposta: str, atendimento_id: str, campaign: str,
    decisao: str, evidencia: str, usuario: str, ocorrido_em: str,
    propostas: Iterable[Mapping[str, Any]],
    atendimentos: Iterable[Mapping[str, Any]],
) -> dict[str, str]:
    """Valida existência e ligação inequívoca dos IDs no snapshot oficial.

    Apenas produz um evento para revisão; NÃO persiste nem presume
    que uma mensagem foi recebida a partir de métricas do site.
    """
    number = str(numero_proposta or "").strip()
    aid = str(atendimento_id or "").strip()
    user = str(usuario or "").strip()
    if not number or not aid or not user or len(user) > 80:
        raise ValueError("Informe pedido, atendimento e operador válidos.")
    if decisao not in _DECISIONS or evidencia not in _EVIDENCES:
        raise ValueError("Decisão ou evidência desconhecida.")
    try:
        date = datetime.fromisoformat(str(ocorrido_em).replace("Z", "+00:00"))
        if date.tzinfo is None or date.utcoffset() is None:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError("Data deve estar em ISO 8601 com fuso horário.") from None
    matches = [p for p in propostas
               if str(p.get("numero_proposta") or "").strip() == number]
    contacts = [c for c in atendimentos
                if str(c.get("id") or "").strip() == aid]
    if len(matches) != 1 or len(contacts) != 1:
        raise ValueError("Pedido ou atendimento ausente/duplicado.")
    if str(matches[0].get("atendimento_id") or "").strip() != aid:
        raise ValueError("Pedido não vinculado ao atendimento informado.")
    return {
        "numero_proposta": number,
        "atendimento_id": aid,
        "campaign": clean_campaign(campaign),
        "decisao": decisao,
        "evidencia": evidencia,
        "usuario": user,
        "ocorrido_em": date.isoformat(),
    }


def effective_attributions(events: Iterable[Mapping[str, Any]]) -> list[dict[str, str]]:
    """Resolve histórico somente quando existe uma ordem temporal inequívoca.

    Conflitos no mesmo instante e em identificadores de atendimento invalidam
    a atribuição do pedido; uma revogação posterior elimina a atribuição.
    O chamador deve passar somente eventos previamente validados/auditados.
    """
    groups: dict[str, list[Mapping[str, Any]]] = {}
    for event in events:
        number = str(event.get("numero_proposta") or "").strip()
        if number:
            groups.setdefault(number, []).append(event)
    resolved: list[dict[str, str]] = []
    for number, rows in groups.items():
        parsed = []
        valid = True
        for e in rows:
            try:
                moment = datetime.fromisoformat(str(e.get("ocorrido_em") or "").replace("Z", "+00:00"))
                if moment.tzinfo is None or moment.utcoffset() is None:
                    raise ValueError()
                if e.get("decisao") not in _DECISIONS:
                    raise ValueError()
                campaign = clean_campaign(e.get("campaign"))
                aid = str(e.get("atendimento_id") or "").strip()
                if not aid:
                    raise ValueError()
                parsed.append((moment, campaign, aid, e["decisao"]))
            except (ValueError, TypeError, KeyError):
                valid = False
                break
        if not valid or not parsed:
            continue
        # Mesmo timestamp para diferentes alterações é ambíguo.
        parsed.sort(key=lambda item: item[0])
        if len({row[0] for row in parsed}) != len(parsed):
            continue
        # Um pedido não pode trocar silenciosamente de atendimento.
        if len({row[2] for row in parsed}) != 1:
            continue
        latest = parsed[-1]
        if latest[3] == "confirmar":
            resolved.append({"numero_proposta": number, "campaign": latest[1]})
    return sorted(resolved, key=lambda item: item["numero_proposta"])
