"""HF68: fila de revisao dos vinculos historicos. Exclusivamente leitura."""
from __future__ import annotations
from collections import Counter, defaultdict
import re
from typing import Any


def _texto(item: dict, *campos: str) -> str:
    for campo in campos:
        valor = str(item.get(campo) or "").strip()
        if valor:
            return valor
    return ""


def _telefone(valor: Any) -> str:
    digitos = re.sub(r"\D", "", str(valor or ""))
    if digitos.startswith("55") and len(digitos) > 11:
        digitos = digitos[2:]
    return digitos if len(digitos) in (10, 11) else ""


def fila_conferencia_vinculos(atendimentos: list[dict] | None,
                             propostas: list[dict] | None) -> dict[str, Any]:
    """Nao associa automaticamente. ID duplicado nao e vinculo confiavel."""
    ids = defaultdict(list)
    telefones = defaultdict(list)
    for a in atendimentos or []:
        if not isinstance(a, dict):
            continue
        aid = _texto(a, "id")
        if not aid:
            continue
        ids[aid].append(a)
        tel = _telefone(_texto(a, "telefone", "whatsapp"))
        if tel:
            telefones[tel].append(aid)

    numeros = Counter(
        _texto(p, "numero_proposta") for p in propostas or []
        if isinstance(p, dict) and _texto(p, "numero_proposta")
    )
    saida = []
    totais = Counter()
    for indice, p in enumerate(propostas or []):
        if not isinstance(p, dict):
            continue
        numero = _texto(p, "numero_proposta")
        aid = _texto(p, "atendimento_id")
        if not numero:
            tipo = "Proposta sem numero"
        elif numeros[numero] > 1:
            tipo = "Numero de proposta repetido"
        elif not aid:
            tipo = "Sem atendimento vinculado"
        elif aid not in ids:
            tipo = "Atendimento nao encontrado"
        elif len(ids[aid]) > 1:
            tipo = "ID de atendimento repetido"
        else:
            continue
        totais[tipo] += 1
        tel = _telefone(_texto(p, "whatsapp", "cliente_wa"))
        candidatos = sorted(set(telefones.get(tel, []))) if tel else []
        # Pistas nao sao provas, inclusive quando existe apenas um candidato.
        if tipo in ("Proposta sem numero", "Numero de proposta repetido"):
            orientacao = "Conferir identidade e duplicidade no Historico antes de qualquer vinculo."
        elif tipo == "ID de atendimento repetido":
            orientacao = "Conferir IDs duplicados na Central antes de atribuir origem."
        elif len(candidatos) > 1:
            orientacao = "Ha multiplos atendimentos com o mesmo telefone: conferir documentos e conversa."
        elif candidatos:
            orientacao = "Conferir manualmente proposta, cliente e conversa; telefone sozinho nao comprova vinculo."
        else:
            orientacao = "Localizar atendimento real e conferir a origem; nao inferir pelo nome."
        saida.append({
            "Proposta": numero or "Sem numero",
            "Situacao": tipo,
            "ID informado": aid or "—",
            "Pistas de atendimento (nao verificadas)": ", ".join(candidatos[:5]) or "Nenhuma",
            "Orientacao": orientacao,
            "_indice": indice,
        })
    ordem = {
        "Numero de proposta repetido": 0, "Proposta sem numero": 1,
        "ID de atendimento repetido": 2, "Atendimento nao encontrado": 3,
        "Sem atendimento vinculado": 4,
    }
    saida.sort(key=lambda x: (ordem[x["Situacao"]], x["_indice"]))
    for linha in saida:
        del linha["_indice"]
    return {"total": len(saida), "por_situacao": dict(totais), "registros": saida}
