"""Controle manual, auditável e seguro de competências DAS-MEI (HF65.24.15).
Não emite guia fiscal nem consulta automaticamente a Receita Federal.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

DOC_KEY = "das_mei_controle_db"
LOCAL_PATH = "das_mei_controle_db.json"
PGMEI_URL = "https://www.gov.br/pt-br/servicos/emitir-das-para-pagamento-de-tributos-do-mei"
STATUSES = ("A emitir", "Emitida / a pagar", "Paga")


def date_due(year: int, month: int) -> date:
    """Vencimento habitual, ajustando sábado/domingo. Feriados exigem conferência."""
    year = int(year) + (int(month) == 12)
    month = 1 if int(month) == 12 else int(month) + 1
    d = date(year, month, 20)
    while d.weekday() > 4:
        d += timedelta(days=1)
    return d


def new_record(year: int, month: int) -> dict[str, Any]:
    if not 2000 <= int(year) <= 2200 or not 1 <= int(month) <= 12:
        raise ValueError("Competência inválida")
    key = f"{int(year):04d}-{int(month):02d}"
    return {"competencia":key,"vencimento":date_due(year,month).isoformat(),"status":"A emitir",
            "valor":None,"emitido_em":"","pago_em":"","guia_path":"","comprovante_path":"",
            "observacoes":"","historico":[]}


def normalize(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict): payload = {}
    registros = payload.get("registros") if isinstance(payload.get("registros"), dict) else {}
    return {"registros":registros}


def money(value: Any) -> float | None:
    if value in (None, ""): return None
    try:
        number=Decimal(str(value).strip().replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")) if isinstance(value,str) and "," in value else Decimal(str(value))
        if number < 0 or number > 100000: raise ValueError("Valor fora da faixa")
        return float(number.quantize(Decimal("0.01")))
    except (InvalidOperation,ValueError): raise ValueError("Informe um valor monetário válido")


def status_of(record: dict, today: date) -> str:
    if record.get("status") == "Paga": return "Paga"
    try:
        due=date.fromisoformat(record.get("vencimento",""))
    except ValueError:
        return str(record.get("status") or "A emitir")
    if due < today: return "Vencida"
    return str(record.get("status") or "A emitir")


def change(record: dict, updates: dict, actor: str, now: datetime) -> dict:
    new=dict(record)
    before={k:new.get(k) for k in updates}
    new.update(updates)
    if new.get("status") not in STATUSES: raise ValueError("Situação inválida")
    if new["status"] == "Paga":
        if not new.get("pago_em") or new.get("valor") is None:
            raise ValueError("Para confirmar pagamento, informe a data e o valor da guia")
    hist=list(record.get("historico") or [])
    changed=[key for key in updates if before[key] != new.get(key)]
    if changed:
        hist.append({"quando":now.isoformat(),"por":str(actor)[:80],"alteracoes":changed,
                     "anterior":before})
    new["historico"]=hist[-100:]
    return new


def totals(records: dict, year: int, today: date) -> dict:
    values=[x for k,x in records.items() if k.startswith(f"{int(year):04d}-") and isinstance(x,dict)]
    return {"competencias":len(values),"a_emitir":sum(status_of(x,today)=="A emitir" for x in values),
            "a_pagar":sum(status_of(x,today)=="Emitida / a pagar" for x in values),
            "vencidas":sum(status_of(x,today)=="Vencida" for x in values),
            "pagas":sum(status_of(x,today)=="Paga" for x in values),
            "total_pago":round(sum(float(x.get("valor") or 0) for x in values if status_of(x,today)=="Paga"),2)}
