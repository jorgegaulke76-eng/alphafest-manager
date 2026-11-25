"""HF56: conferência comercial pura antes de gravar um orçamento.

Não lê banco, relógio, catálogo nem estado da interface e não altera a proposta.
Os valores do resumo são Decimal (ou None quando o cálculo é inválido), sem
arredondamento de linha. ``pode_salvar`` informa apenas a ausência de bloqueios;
o chamador ainda precisa obter o aceite dos avisos que o exigirem.

Índices de itens começam em zero; as mensagens apresentam a linha a partir de 1.
As assinaturas vinculam todo o payload, inclusive metadados e personalizações,
mas não representam uma autorização para gravar.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal, DecimalException, Inexact, InvalidOperation, Overflow, localcontext
import hashlib
import json
import re
from typing import Any


_ZERO = Decimal("0")
_CENTAVO = Decimal("0.01")
_SCHEMA = "hf56-revisao-v1"
_NUMERO = re.compile(r"[+-]?[0-9]+(?:[.,][0-9]+)?")
# Protege a conferência de dados corrompidos com milhões de casas decimais.
# Não é um teto comercial; os campos comuns usam poucas dezenas de dígitos.
_MAX_PRECISAO = 10_000


def _texto(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _numero(value: Any) -> Decimal | None:
    """Aceita decimal simples BR/ISO; nunca supõe um separador de milhar.

    Um ponto único continua sendo decimal, inclusive em strings legadas com
    três casas, conforme o cálculo do Manager. Agrupamentos não são aceitos.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        return None
    try:
        if isinstance(value, str):
            text = value.strip()
            if not _NUMERO.fullmatch(text):
                return None
            result = Decimal(text.replace(",", "."))
        elif isinstance(value, Decimal):
            result = value
        elif isinstance(value, int):
            result = Decimal(value)
        else:
            result = Decimal(str(value))
        return result if result.is_finite() else None
    except (DecimalException, TypeError, ValueError, OverflowError):
        return None


def _somar(values: list[Decimal]) -> Decimal:
    """Soma exata, independente da precisão Decimal do processo chamador."""
    if not values:
        return _ZERO
    precision = max(28, max(v.adjusted() for v in values)
                    - min(v.as_tuple().exponent for v in values)
                    + len(str(len(values))) + 2)
    if precision > _MAX_PRECISAO:
        raise InvalidOperation("Precisão impraticável para a conferência.")
    with localcontext() as context:
        context.prec = precision
        context.Emax, context.Emin = 999999, -999999
        context.traps[Inexact] = context.traps[Overflow] = context.traps[InvalidOperation] = True
        result = sum(values, _ZERO)
    if not result.is_finite():
        raise InvalidOperation("Resultado não finito.")
    return result


def _multiplicar(left: Decimal, right: Decimal) -> Decimal:
    precision = max(28, len(left.as_tuple().digits) + len(right.as_tuple().digits) + 1)
    if precision > _MAX_PRECISAO:
        raise InvalidOperation("Precisão impraticável para a conferência.")
    with localcontext() as context:
        context.prec = precision
        context.Emax, context.Emin = 999999, -999999
        context.traps[Inexact] = context.traps[Overflow] = context.traps[InvalidOperation] = True
        result = left * right
    if not result.is_finite():
        raise InvalidOperation("Resultado não finito.")
    return result


def _data(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    patterns = ((r"[0-9]{2}/[0-9]{2}/[0-9]{4}", "%d/%m/%Y"),
                (r"[0-9]{4}-[0-9]{2}-[0-9]{2}", "%Y-%m-%d"))
    for expression, pattern in patterns:
        if re.fullmatch(expression, text):
            try:
                return datetime.strptime(text, pattern).date()
            except ValueError:
                return None
    return None


def conferir_orcamento(proposta, hoje, *, em_edicao=False, item_pendente=False) -> dict:
    """Confere todos os campos e linhas sem corrigir ou completar o rascunho.

    Subtotal e total informados são obrigatórios no snapshot do formulário e
    podem divergir em até um centavo do cálculo independente. Para Retirada,
    uma taxa não nula é inconsistente e precisa ser corrigida explicitamente.
    Datas aceitam dd/mm/aaaa, aaaa-mm-dd e objetos date/datetime. Prazos aceitam
    valores numericamente inteiros positivos; texto livre permanece visível
    no formulário e exige conferência, sem ser reescrito pelo serviço.
    """
    bloqueios: list[dict] = []
    avisos: list[dict] = []

    def bloquear(codigo, mensagem, indice=None):
        record = {"codigo": codigo, "mensagem": mensagem}
        if indice is not None:
            record["indice"] = indice
        bloqueios.append(record)

    def avisar(codigo, mensagem, indice=None, *, exigir_confirmacao=True):
        record = {"codigo": codigo, "mensagem": mensagem,
                  "exigir_confirmacao": exigir_confirmacao}
        if indice is not None:
            record["indice"] = indice
        avisos.append(record)

    if not isinstance(proposta, Mapping):
        bloquear("proposta_invalida", "O rascunho não contém um orçamento válido. Reabra o formulário.")
        proposta = {}

    if not _texto(proposta.get("cliente_nome")).strip():
        bloquear("cliente_vazio", "Informe o nome do cliente.")
    if not _texto(proposta.get("whatsapp")).strip():
        avisar("whatsapp_vazio", "WhatsApp não informado. O orçamento pode ser salvo para atendimento presencial.",
               exigir_confirmacao=False)

    items = proposta.get("itens")
    if not isinstance(items, (list, tuple)):
        bloquear("itens_invalidos", "A lista de itens do orçamento está inválida. Reabra e confira os itens.")
        items = []
    elif not items:
        bloquear("sem_itens", "Adicione pelo menos um item ao orçamento.")

    rows = []
    for index, item in enumerate(items):
        prefix = f"Item {index + 1}: "
        if not isinstance(item, Mapping):
            bloquear("item_invalido", prefix + "a linha está inválida. Corrija ou remova este item.", index)
            rows.append({"indice": index, "produto": "", "especificacoes": "",
                         "quantidade": None, "valor_unitario": None, "total": None})
            continue
        produto = _texto(item.get("produto"))
        if not produto.strip():
            bloquear("produto_vazio", prefix + "informe o nome do produto.", index)
        quantity = _numero(item.get("quantidade"))
        price = _numero(item.get("valor_unitario"))
        if quantity is None or quantity <= _ZERO:
            bloquear("quantidade_invalida", prefix + "a quantidade deve ser um número finito maior que zero, sem separador de milhar.", index)
            quantity = None
        if price is None or price < _ZERO:
            bloquear("preco_invalido", prefix + "o valor unitário deve ser um número finito maior ou igual a zero, sem separador de milhar.", index)
            price = None
        elif price == _ZERO:
            avisar("preco_zero", prefix + "o valor unitário está zerado. Confirme se este item será oferecido sem cobrança ou informe o preço.", index)
        total = None
        if quantity is not None and price is not None:
            try:
                total = _multiplicar(quantity, price)
            except DecimalException:
                bloquear("total_item_invalido", prefix + "não foi possível calcular um total válido. Confira a quantidade e o preço.", index)
        rows.append({"indice": index, "produto": produto,
                     "especificacoes": _texto(item.get("especificacoes")),
                     "quantidade": quantity, "valor_unitario": price, "total": total})

    unidades = subtotal = None
    if all(row["quantidade"] is not None for row in rows):
        try:
            unidades = _somar([row["quantidade"] for row in rows])
        except DecimalException:
            bloquear("unidades_invalidas", "Não foi possível somar as quantidades. Confira os itens.")
    if all(row["total"] is not None for row in rows):
        try:
            subtotal = _somar([row["total"] for row in rows])
        except DecimalException:
            bloquear("subtotal_calculado_invalido", "Não foi possível calcular o subtotal. Confira as quantidades e os preços.")

    amounts = {}
    for field, label in (("desconto", "O desconto"), ("taxa_entrega", "A taxa de entrega"),
                         ("subtotal", "O subtotal informado"), ("valor_total", "O total informado")):
        number = _numero(proposta.get(field))
        if number is None or number < _ZERO:
            bloquear(field + "_invalido", label + " deve ser um número finito maior ou igual a zero, sem separador de milhar.")
            number = None
        amounts[field] = number
    desconto, taxa = amounts["desconto"], amounts["taxa_entrega"]
    frete = proposta.get("frete_tipo")
    if frete not in ("Entrega", "Retirada"):
        bloquear("frete_invalido", "Escolha Entrega ou Retirada para o orçamento.")
    elif frete == "Retirada" and taxa is not None and taxa != _ZERO:
        bloquear("taxa_retirada", "O orçamento está como Retirada e possui taxa de entrega. Confira a modalidade ou zere a taxa.")
    if subtotal is not None and desconto is not None and desconto > subtotal:
        bloquear("desconto_excedente", "O desconto é maior que o subtotal dos itens. Corrija o desconto antes de salvar.")

    valor_total = None
    if subtotal is not None and desconto is not None and taxa is not None:
        try:
            # Não aplicar max(..., 0): o desconto excedente é um erro explícito.
            valor_total = _somar([subtotal, desconto.copy_negate(), taxa])
        except DecimalException:
            bloquear("total_calculado_invalido", "Não foi possível calcular o total. Confira os valores do orçamento.")
    for field, calculated, label in (("subtotal", subtotal, "subtotal"),
                                     ("valor_total", valor_total, "total")):
        supplied = amounts[field]
        if supplied is not None and calculated is not None:
            try:
                difference = _somar([supplied, calculated.copy_negate()]).copy_abs()
                if difference > _CENTAVO:
                    bloquear(field + "_divergente", f"O {label} informado diverge do cálculo dos itens, desconto e entrega em mais de R$ 0,01. Confira os valores antes de salvar.")
            except DecimalException:
                bloquear(field + "_incomparavel", f"Não foi possível conferir o {label} informado. Confira os valores antes de salvar.")
    if rows and (valor_total == _ZERO or amounts["valor_total"] == _ZERO):
        origem_total = "informado para salvar" if amounts["valor_total"] == _ZERO else "calculado"
        avisar("total_zero", f"O total {origem_total} está zerado. Confirme se a proposta será oferecida sem cobrança.")

    referencia, entrega = _data(hoje), _data(proposta.get("data_entrega"))
    if referencia is None:
        bloquear("data_referencia_invalida", "A data de referência da conferência está inválida. Reabra o formulário.")
    if entrega is None:
        bloquear("data_entrega_invalida", "Informe uma data de entrega válida.")
    elif referencia is not None and entrega < referencia and not em_edicao:
        avisar("entrega_passada", "A data de entrega está no passado. Confirme se esta é a data desejada para o novo orçamento.")
    for field, label in (("prazo_dias", "Prazo de produção"), ("validade_dias", "Validade do orçamento")):
        number = _numero(proposta.get(field))
        if number is None or number <= _ZERO or number != number.to_integral_value():
            avisar(field + "_pendente", label + ": informe um número inteiro de dias maior que zero ou confirme a condição registrada no campo.")
    if item_pendente:
        avisar("item_pendente", "Há um produto selecionado ou campos de item já confirmados que ainda não foram adicionados. Confira se deseja incluir esse item antes de salvar.")

    return {"bloqueios": bloqueios, "avisos": avisos,
            "resumo": {"linhas": len(rows), "unidades": unidades, "subtotal": subtotal,
                       "desconto": desconto, "taxa_entrega": taxa,
                       "valor_total": valor_total, "itens": rows},
            "pode_salvar": not bloqueios}


def _canonico(value: Any, ativos: set[int]) -> Any:
    """Serializa dados inválidos de maneira tipada, sem liberar sua gravação."""
    if value is None:
        return ["nulo"]
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, str):
        return ["texto", value]
    if isinstance(value, (int, float, Decimal)):
        try:
            number = value if isinstance(value, Decimal) else Decimal(value) if isinstance(value, int) else Decimal(str(value))
            if not number.is_finite():
                return ["numero_nao_finito", str(number)]
            # A tupla evita expandir expoentes extremos e não arredonda.
            sign, digits, exponent = number.as_tuple()
            digits = list(digits)
            if not any(digits):
                return ["numero", 0, [0], 0]
            while len(digits) > 1 and digits[-1] == 0:
                digits.pop()
                exponent += 1
            return ["numero", sign, digits, exponent]
        except (DecimalException, TypeError, ValueError, OverflowError):
            return ["numero_invalido", type(value).__name__]
    if isinstance(value, datetime):
        return ["datetime", value.isoformat()]
    if isinstance(value, date):
        return ["data", value.isoformat()]
    if id(value) in ativos:
        return ["referencia_circular", type(value).__name__]
    if isinstance(value, (Mapping, list, tuple, set, frozenset)):
        ativos.add(id(value))
        try:
            if isinstance(value, Mapping):
                pairs = [[_canonico(key, ativos), _canonico(item, ativos)] for key, item in value.items()]
                pairs.sort(key=lambda pair: json.dumps(pair[0], ensure_ascii=False, separators=(",", ":")))
                return ["objeto", pairs]
            values = [_canonico(item, ativos) for item in value]
            if isinstance(value, (set, frozenset)):
                values.sort(key=lambda item: json.dumps(item, ensure_ascii=False, separators=(",", ":")))
                return ["conjunto", values]
            return ["lista", values]
        finally:
            ativos.remove(id(value))
    if isinstance(value, bytes):
        return ["bytes", value.hex()]
    # Os formulários usam apenas os tipos acima. Um tipo inesperado ainda pode
    # ser exibido como inválido sem derrubar a assinatura nem apagar o rascunho.
    return ["tipo_nao_suportado", type(value).__module__, type(value).__qualname__, repr(value)]


def assinatura_revisao(proposta, resultado, *, contexto=None) -> str:
    """Vincula payload completo, resultado e contexto ao aceite desta revisão.

    A ordem das chaves não importa; a ordem/multiplicidade dos itens importa.
    NaN/Inf permanecem distinguíveis e assináveis para renderizar bloqueios.
    Nenhum campo é removido nem convertido no objeto recebido.
    """
    payload = {"schema": _SCHEMA, "proposta": proposta,
               "resultado": resultado, "contexto": contexto}
    serialized = json.dumps(_canonico(payload, set()), ensure_ascii=False,
                            separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
