"""HF55: indícios de propostas repetidas, sem leitura, gravação ou confirmação.

Uma correspondência exige evidência de cliente em comum e, adicionalmente, a
mensagem original do site ou o mesmo multiconjunto de linhas do pedido. Preços
não decidem a correspondência. Cada linha, quantidade e personalização conta;
linhas repetidas nunca são fundidas. Pedidos recorrentes continuam possíveis.

O chamador fornece o histórico completo e a data de referência. A janela inclui
hoje e os ``dias - 1`` dias anteriores. Registros encerrados e entregues também
participam. Ausência de candidatos não prova ausência de duplicidade, sobretudo
quando datas ou identificadores estão ausentes. As assinaturas servem para
invalidar uma conferência quando o pedido ou os candidatos mudam; não são uma
autorização nem um mecanismo de gravação.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import re
import unicodedata
from typing import Any

from proposal_status import resumo_status


SOURCE_PREFIX = "Mensagem recebida do site:\n"
_SCHEMA = "hf55-duplicidades-v1"


def _texto(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return ""


def _campo(record: Mapping[str, Any], *names: str) -> str:
    for name in names:
        value = _texto(record.get(name))
        if value:
            return value
    return ""


def _comparavel(value: str) -> str:
    # Sem fuzzy, remoção de acentos ou de pontuação das personalizações.
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _numero_decimal(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError("A conferência recebeu um número não finito.")
    if value == 0:
        return "0"
    # Não usar normalize(): a precisão do contexto Decimal não deve arredondar.
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _canonico(value: Any) -> Any:
    """Representação tipada estável; nenhuma chave ou campo é descartado."""
    if value is None:
        return ["nulo"]
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, str):
        return ["texto", value]
    if isinstance(value, (int, float, Decimal)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("A conferência recebeu um número não finito.")
        return ["numero", _numero_decimal(Decimal(str(value)))]
    if isinstance(value, datetime):
        return ["datetime", value.isoformat()]
    if isinstance(value, date):
        return ["data", value.isoformat()]
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("Os campos da conferência precisam ter nomes em texto.")
        return ["objeto", [[key, _canonico(value[key])] for key in sorted(value)]]
    if isinstance(value, (list, tuple)):
        return ["lista", [_canonico(item) for item in value]]
    raise ValueError("A conferência recebeu um tipo de dado não suportado.")


def _serializar(value: Any) -> str:
    return json.dumps(_canonico(value), ensure_ascii=False, separators=(",", ":"))


def _assinatura(value: Any) -> str:
    return hashlib.sha256(_serializar(value).encode("utf-8")).hexdigest()


def assinatura_proposta(proposta: Mapping[str, Any]) -> str:
    """Vincula a conferência a todo o payload, inclusive preços e contexto.

    Chaves de dicionário não têm ordem; listas, incluindo as linhas do pedido,
    mantêm sua ordem. Tipos incompatíveis ou números não finitos causam erro
    explícito, em vez de produzirem uma aprovação para um payload incompleto.
    """
    if not isinstance(proposta, Mapping):
        raise ValueError("A proposta para conferência precisa ser um objeto.")
    return _assinatura({"schema": _SCHEMA, "proposta": proposta})


def assinatura_conferencia(proposta: Mapping[str, Any], resultado: Mapping[str, Any]) -> str:
    """Assina payload, janela e todos os candidatos, sem contagens alheias.

    Incluir ou alterar uma proposta sem correspondência não invalida o aceite
    dos mesmos candidatos. Reordenar histórico/candidatos também não invalida.
    Campos e assinatura de cada candidato entram integralmente na prova.
    """
    if not isinstance(resultado, Mapping):
        raise ValueError("O resultado da conferência precisa ser um objeto.")
    required = ("candidatos", "janela_dias", "data_inicio", "data_fim")
    if any(key not in resultado for key in required):
        raise ValueError("O resultado da conferência está incompleto.")
    candidates = resultado["candidatos"]
    if not isinstance(candidates, (list, tuple)) or any(not isinstance(c, Mapping) for c in candidates):
        raise ValueError("A lista de candidatos da conferência é inválida.")
    # Ordenar a representação, preservando inclusive a multiplicidade.
    return _assinatura({
        "schema": _SCHEMA,
        "proposta": assinatura_proposta(proposta),
        "janela_dias": resultado["janela_dias"],
        "data_inicio": resultado["data_inicio"],
        "data_fim": resultado["data_fim"],
        "candidatos": sorted(_serializar(candidate) for candidate in candidates),
    })


def _data(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    for pattern in ("%d/%m/%Y", "%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            pass
    try:
        # O calendário é o da data fornecida; não inferir fuso nem consultar relógio.
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _documento(text: str) -> str:
    if not text or not re.fullmatch(r"[0-9.\-/\s]+", text):
        return ""
    digits = re.sub(r"\D", "", text)
    return digits if len(digits) in (11, 14) and len(set(digits)) > 1 else ""


def _telefone(text: str) -> str:
    if not text or not re.fullmatch(r"\+?[0-9().\-\s]+", text):
        return ""
    digits = re.sub(r"\D", "", text)
    # Só retirar DDI quando sobram DDD + número de 10/11 dígitos. DDD 55 local
    # nunca é removido, nem se adivinha o nono dígito ou números incompletos.
    if digits.startswith("0055") and len(digits) in (14, 15):
        digits = digits[4:]
    elif digits.startswith("55") and len(digits) in (12, 13):
        digits = digits[2:]
    return digits if 10 <= len(digits) <= 15 and len(set(digits)) > 1 else ""


def _identidade(record: Mapping[str, Any]) -> dict[str, str]:
    doc = _campo(record, "documento", "cliente_cpf_cnpj")
    phone = _campo(record, "whatsapp", "cliente_wa")
    document_key = _documento(doc)
    phone_key = _telefone(phone)
    return {
        "nome": _comparavel(_campo(record, "cliente_nome", "cliente")),
        "documento": document_key,
        "whatsapp": phone_key,
        # Um valor malformado também não deve esconder uma contradição entre
        # campos preenchidos. Esses valores internos nunca saem no candidato.
        "documento_preenchido": document_key or _comparavel(doc),
        "whatsapp_preenchido": phone_key or _comparavel(phone),
        "relacionamento": _campo(record, "relacionamento_id"),
        "invalido": "sim" if (doc and not document_key) or (phone and not phone_key) else "",
    }


def _mesmo_cliente(left: Mapping[str, str], right: Mapping[str, str]) -> tuple[str, str] | None:
    keys = ("documento", "whatsapp", "relacionamento")
    # Conflitos têm precedência sobre nome e identificadores coincidentes.
    # A revisão não deve sugerir clientes homônimos com contatos contraditórios.
    conflicts = ("documento_preenchido", "whatsapp_preenchido", "relacionamento")
    if any(left[key] and right[key] and left[key] != right[key] for key in conflicts):
        return None
    reasons = {
        "documento": "Mesmo documento do cliente.",
        "whatsapp": "Mesmo WhatsApp do cliente (DDI 55 normalizado quando aplicável).",
        "relacionamento": "Mesmo cadastro de relacionamento do cliente.",
    }
    for key in keys:
        if left[key] and left[key] == right[key]:
            return key, reasons[key]
    if left["invalido"] or right["invalido"]:
        return None
    if left["nome"] and left["nome"] == right["nome"]:
        return "nome", "Nome exato do cliente, sem identificador comum: indício fraco; confirme se é a mesma pessoa."
    return None


def _origem_site(record: Mapping[str, Any]) -> str:
    text = record.get("briefing_origem")
    if not isinstance(text, str) or not text.startswith(SOURCE_PREFIX):
        return ""
    original = text[len(SOURCE_PREFIX):]
    # Exigir original não vazio e comparar seu conteúdo integral, sem ignorar
    # caixa, personalizações ou trechos. Observações comuns nunca são origem.
    return original if original.strip() else ""


def _quantidade(value: Any) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        return None
    text = str(value).strip()
    if isinstance(value, str):
        # Aceitar decimal simples BR/ISO, sem adivinhar separador de milhar.
        if not re.fullmatch(r"\+?\d+(?:[.,]\d+)?", text):
            return None
        if re.fullmatch(r"\+?[1-9]\d{0,2}(?:\.\d{3})+", text):
            return None
        text = text.replace(",", ".")
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None
    return number if number.is_finite() and number > 0 else None


def _itens(record: Mapping[str, Any]) -> list[dict[str, Any]] | None:
    items = record.get("itens")
    if not isinstance(items, (list, tuple)) or not items:
        return None
    result = []
    for item in items:
        if not isinstance(item, Mapping):
            return None
        product_id = _campo(item, "produto_catalogo_id")
        name = _comparavel(_campo(item, "produto"))
        quantity = _quantidade(item.get("quantidade"))
        note = item.get("especificacoes", "")
        if quantity is None or not (product_id or name) or not isinstance(note, (str, type(None))):
            return None
        result.append({
            "id": product_id,
            "nome": name,
            "quantidade": quantity,
            "nota": _comparavel(note or ""),
            "unidade": _comparavel(_campo(item, "unidade", "unidade_medida")),
        })
    return result


def _mesma_linha(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    if any(left[key] != right[key] for key in ("quantidade", "nota", "unidade")):
        return False
    if left["id"] and right["id"]:
        return left["id"] == right["id"]
    return bool(left["nome"]) and left["nome"] == right["nome"]


def _mesmos_itens(left: list[dict[str, Any]] | None, right: list[dict[str, Any]] | None) -> bool:
    if not left or not right or len(left) != len(right):
        return False
    # Emparelhamento completo: uma linha legada sem ID não deve consumir a
    # única linha que pode corresponder a outra com ID. Cada ocorrência vale 1.
    edges = [[j for j, other in enumerate(right) if _mesma_linha(item, other)] for item in left]
    if any(not neighbors for neighbors in edges):
        return False
    matched_right: dict[int, int] = {}
    matched_left: dict[int, int] = {}
    for start in sorted(range(len(left)), key=lambda i: len(edges[i])):
        queue = deque([start])
        previous: dict[int, int] = {}
        free_target = None
        while queue and free_target is None:
            index = queue.popleft()
            for target in edges[index]:
                if target in previous:
                    continue
                previous[target] = index
                if target not in matched_right:
                    free_target = target
                    break
                queue.append(matched_right[target])
        if free_target is None:
            return False
        # Reconstruir caminho alternante sem recursão/limite de profundidade.
        target = free_target
        while target is not None:
            index = previous[target]
            old_target = matched_left.get(index)
            matched_right[target] = index
            matched_left[index] = target
            target = old_target
    return True


def _status(record: Mapping[str, Any]) -> str:
    state = resumo_status(record)
    if state["encerrada"]:
        return "Encerrada/cancelada"
    if state["entregue"]:
        return "Entregue"
    if state["pronto"]:
        return "Pronta para entrega"
    if state["aprovado"]:
        return "Aprovada / em andamento"
    return "Aguardando aprovação"


def _resumo(record: Mapping[str, Any], items: list[dict[str, Any]] | None) -> str:
    if items:
        quantity = sum((item["quantidade"] for item in items), Decimal(0))
        text = f"{len(items)} linha(s) · {_numero_decimal(quantity)} unidade(s)"
    else:
        text = "Itens sem dados suficientes para comparação"
    delivery = _data(record.get("data_entrega"))
    if delivery:
        text += f" · entrega prevista em {delivery.strftime('%d/%m/%Y')}"
    return text


def analisar_duplicidades(
    proposta: Mapping[str, Any], historico: list[Mapping[str, Any]], hoje: date | str,
    *, dias: int = 30, excluir_numero: str = "",
) -> dict[str, Any]:
    """Retorna todos os indícios recentes, sem mutar proposta ou histórico.

    ``data_geracao`` aceita data brasileira ou ISO (inclusive datetime). Datas
    ausentes/inválidas e futuras ficam fora da busca, com contagens explícitas.
    ``excluir_numero`` só exclui uma edição quando fornecido expressamente; o
    número do payload nunca exclui um registro automaticamente.

    Identidade: documento, WhatsApp ou relacionamento coincidente, sem conflitos
    entre identificadores preenchidos. Sem identificador comum, nome normalizado
    exato é apenas indício fraco. Identificadores malformados não habilitam esse
    fallback. Não há verificação externa de titularidade/CPF nem fuzzy matching.
    """
    if not isinstance(proposta, Mapping):
        raise ValueError("A proposta para conferência precisa ser um objeto.")
    if not isinstance(historico, (list, tuple)):
        raise ValueError("O histórico de propostas precisa ser uma lista; a conferência não foi realizada.")
    for index, record in enumerate(historico):
        if not isinstance(record, Mapping):
            raise ValueError(f"Histórico inválido: o registro na posição {index + 1} não é uma proposta.")
    if isinstance(dias, bool) or not isinstance(dias, int) or dias < 1:
        raise ValueError("A janela da conferência precisa ser um número inteiro positivo de dias.")
    today = _data(hoje)
    if today is None:
        raise ValueError("A data de referência da conferência é inválida.")
    try:
        start = today - timedelta(days=dias - 1)
    except (OverflowError, ValueError) as exc:
        raise ValueError("A janela de datas da conferência é inválida.") from exc
    identity = _identidade(proposta)
    source = _origem_site(proposta)
    proposal_items = _itens(proposta)
    excluded_number = _texto(excluir_numero)
    result: dict[str, Any] = {
        "candidatos": [], "avaliados": 0, "sem_data": 0,
        "fora_janela": 0, "futuros": 0, "excluidos": 0,
        "itens_incomparaveis": 0, "janela_dias": dias,
        "data_inicio": start.isoformat(), "data_fim": today.isoformat(),
        "avisos": [],
    }
    for record in historico:
        number = _campo(record, "numero_proposta")
        if excluded_number and number == excluded_number:
            result["excluidos"] += 1
            continue
        generated = _data(record.get("data_geracao"))
        if generated is None:
            result["sem_data"] += 1
            continue
        if generated > today:
            result["futuros"] += 1
            continue
        if generated < start:
            result["fora_janela"] += 1
            continue
        result["avaliados"] += 1
        record_items = _itens(record)
        if record_items is None:
            result["itens_incomparaveis"] += 1
        customer = _mesmo_cliente(identity, _identidade(record))
        if not customer:
            continue
        matches = []
        reasons = [customer[1]]
        if source and source == _origem_site(record):
            matches.append("origem_site")
            reasons.append("Mesma mensagem original recebida do site.")
        if _mesmos_itens(proposal_items, record_items):
            matches.append("itens")
            reasons.append("Mesmas linhas de produtos, quantidades e personalizações; preços não são comparados.")
        if not matches:
            continue
        result["candidatos"].append({
            "numero": number,
            "data": generated.strftime("%d/%m/%Y"), "data_iso": generated.isoformat(),
            "cliente": _campo(record, "cliente_nome", "cliente"),
            "motivos": reasons, "identidade": customer[0],
            "correspondencias": matches, "status": _status(record),
            "resumo": _resumo(record, record_items), "assinatura": assinatura_proposta(record),
        })
    result["candidatos"].sort(key=lambda c: (c["data_iso"], c["numero"], c["assinatura"]), reverse=True)
    if result["sem_data"]:
        result["avisos"].append(f"{result['sem_data']} registro(s) sem data de geração válida ficaram fora da conferência.")
    if result["futuros"]:
        result["avisos"].append(f"{result['futuros']} registro(s) com data de geração futura ficaram fora da conferência.")
    if result["itens_incomparaveis"]:
        result["avisos"].append(f"{result['itens_incomparaveis']} registro(s) recentes sem itens comparáveis só puderam ser verificados pela mensagem original do site.")
    if proposal_items is None:
        result["avisos"].append("O pedido atual não possui itens suficientes para comparação; apenas a mensagem original do site pode ser comparada.")
    if not any(identity[key] for key in ("nome", "documento", "whatsapp", "relacionamento")):
        result["avisos"].append("O pedido atual não possui identificação de cliente suficiente para buscar possíveis duplicidades.")
    if identity["invalido"]:
        result["avisos"].append("Há identificador de cliente em formato não comparável; o nome sozinho não será usado como indício.")
    return result
