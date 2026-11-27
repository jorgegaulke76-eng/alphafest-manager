"""Importação revisável do texto do carrinho AlphaFest, sem banco ou rede.

A mensagem é evidência da solicitação, não uma fonte de preço, cadastro ou
aprovação de pedido. Somente correspondências únicas de nome/alias no catálogo
ativo sugerem identidade e preço. A revisão humana conserva todas as linhas.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from collections.abc import Mapping

from catalogo_orcamento_service import aliases_catalogo_atomicos, normalizar_identidade_produto


MAX_TEXT_LENGTH = 100_000
MAX_ITEMS = 100
MAX_QUANTITY = 1_000_000
MAX_UNIT_VALUE = 1_000_000_000
SOURCE_PREFIX = "Mensagem recebida do site:\n"
SITE_INTRO = "Olá! Gostaria de solicitar um orçamento na AlphaFest para os seguintes produtos:"
SITE_END = "Podem confirmar valores, disponibilidade, prazo e opções de retirada/entrega? Obrigado!"

_HEADER = re.compile(r"^[ \t]*(\d{1,6})[.)][ \t]+(.*?)[ \t]*$")
_QUANTITY = re.compile(r"^[ \t]*(?:Quantidade|Qtd\.?)[ \t]*:[ \t]*(.*?)[ \t]*$", re.I)
_QUANTITY_LIKE = re.compile(r"^[ \t]*(?:Quantidade|Qtd\.?)(?:[ \t:]|$)", re.I)
_NOTE = re.compile(r"^[ \t]*(?:Personaliza[çc][ãa]o/observa[çc][õo]es|Personaliza[çc][ãa]o|Observa[çc][õo]es)[ \t]*:[ \t]?(.*)$", re.I)
_IDENTITY_FIELDS = ("produto_origem", "produto_digitado", "produto_catalogo_id")


def _records(catalogo):
    if catalogo is None:
        return []
    if not isinstance(catalogo, (list, tuple)):
        raise ValueError("O catálogo recebido não é uma lista. Recarregue e analise novamente.")
    return [item for item in catalogo if isinstance(item, Mapping)]


def _active(produto):
    # Ausência mantém a convenção do catálogo. Flags malformadas não autorizam
    # associar automaticamente uma solicitação a um produto.
    return produto.get("Ativo", True) is True


def assinatura_catalogo(catalogo):
    """Assina somente dados usados na correspondência e na sugestão de preço.

    Reordenar registros/aliases ou mudar fotos não invalida a revisão; mudar
    identidade, disponibilidade ou preço exige uma análise nova.
    """
    relevant = []
    for produto in _records(catalogo):
        relevant.append({
            "nome": str(produto.get("Nome") or "").strip(),
            "aliases": sorted(set(aliases_catalogo_atomicos(produto))),
            "ativo": _active(produto),
            "id": str(produto.get("CatalogoId") or produto.get("id") or ""),
            "preco": str(produto.get("Preco", produto.get("preco", "")) or ""),
        })
    serialized = sorted(json.dumps(p, ensure_ascii=False, sort_keys=True) for p in relevant)
    return hashlib.sha256(json.dumps(serialized, ensure_ascii=False).encode("utf-8")).hexdigest()


def _number(value, *, currency=False):
    if isinstance(value, bool) or value is None:
        raise ValueError("Número ausente ou inválido.")
    if isinstance(value, (int, float, Decimal)):
        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise ValueError("Número inválido.") from None
    elif isinstance(value, str):
        text = value.strip()
        if currency and text.startswith("R$"):
            text = text[2:].strip()
        if "," in text:
            if not re.fullmatch(r"[+-]?(?:\d{1,3}(?:\.\d{3})+|\d+),\d+", text):
                raise ValueError("Use um número válido, com vírgula para os decimais.")
            text = text.replace(".", "").replace(",", ".")
        elif not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", text):
            raise ValueError("Use um número válido.")
        try:
            number = Decimal(text)
        except InvalidOperation:
            raise ValueError("Número inválido.") from None
    else:
        raise ValueError("Número inválido.")
    if not number.is_finite():
        raise ValueError("O número deve ser finito.")
    return number


def _quantity(value):
    if isinstance(value, str) and re.fullmatch(r"[+-]?\d{1,3}\.\d{3}", value.strip()):
        raise ValueError("Quantidade com ponto ambíguo; use dígitos sem separador ou vírgula decimal.")
    number = _number(value)
    if not 0 < number <= MAX_QUANTITY:
        raise ValueError(f"A quantidade deve ser positiva e no máximo {MAX_QUANTITY:,}.".replace(",", "."))
    result = int(number) if number == number.to_integral_value() else float(number)
    if result <= 0:
        raise ValueError("Quantidade pequena demais para representar no orçamento.")
    return result


def _price(value):
    number = _number(value, currency=True)
    if not 0 <= number <= MAX_UNIT_VALUE:
        raise ValueError("O valor unitário deve ser de zero a R$ 1.000.000.000.")
    return float(number)


def _match_product(name, catalogo):
    key = normalizar_identidade_produto(name)
    matches = []
    for produto in catalogo:
        official = str(produto.get("Nome") or "").strip()
        if not official or not key:
            continue
        official_match = normalizar_identidade_produto(official) == key
        alias_match = any(normalizar_identidade_produto(alias) == key for alias in aliases_catalogo_atomicos(produto))
        if official_match or alias_match:
            matches.append((produto, official_match))
    active = [(p, exact) for p, exact in matches if _active(p)]
    result = {
        "produto": name, "produto_origem": "livre", "produto_digitado": name,
        "produto_catalogo_id": "", "valor_unitario": 0.0,
        "status_catalogo": "nao_encontrado", "avisos": [],
    }
    if len(active) > 1:
        result["status_catalogo"] = "ambiguo"
        result["avisos"].append("Mais de um produto ativo corresponde a este nome/alias. Mantido como texto livre; confira o produto e informe o preço.")
    elif len(active) == 1:
        produto, exact = active[0]
        result.update(
            produto=str(produto["Nome"]).strip(),
            produto_origem="catalogo" if exact else "catalogo_alias",
            produto_catalogo_id=str(produto.get("CatalogoId") or produto.get("id") or ""),
            status_catalogo="encontrado" if exact else "alias",
        )
        try:
            # Mesmos campos do helper oficial _i811_preco_catalogo_float.
            price = _price(produto.get("Preco", produto.get("preco", "")))
        except ValueError:
            price = 0.0
        result["valor_unitario"] = price
        if not price:
            result["avisos"].append("O catálogo não tem preço positivo válido para este item. Informe o valor ou confirme que revisará um item sem preço.")
    elif matches:
        result["status_catalogo"] = "inativo"
        result["avisos"].append("A correspondência está inativa ou com situação inválida no catálogo. Mantida como texto livre, sem preço sugerido.")
    else:
        result["avisos"].append("Produto não encontrado por nome ou alias exato no catálogo ativo. Mantido como texto livre, sem preço sugerido.")
    return result


def analisar_mensagem(texto, catalogo):
    """Interpreta a estrutura numerada do site, preservando a mensagem original.

    Uma linha numerada seguida de Quantidade identifica um produto. Enumerações
    dentro das observações continuam sendo texto. Se a quantidade faltar junto
    da personalização, o item permanece revisável com quantidade None.
    """
    result = {
        "texto_original": texto if isinstance(texto, str) else "",
        "assinatura_catalogo": "", "itens": [], "erros": [], "avisos": [],
        "observacoes_gerais": "",
    }
    if not isinstance(texto, str) or not texto.strip():
        result["erros"].append("Cole a mensagem completa do orçamento recebido do site.")
        return result
    if len(texto) > MAX_TEXT_LENGTH:
        result["erros"].append("A mensagem ultrapassa 100.000 caracteres. Divida a solicitação antes de analisar; nenhum trecho foi importado.")
        return result
    try:
        catalogo = _records(catalogo)
        result["assinatura_catalogo"] = assinatura_catalogo(catalogo)
    except ValueError as exc:
        result["erros"].append(str(exc))
        return result

    lines = texto.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    # O fecho padrão não faz parte da personalização. Texto acrescentado após
    # ele continua preservado nas observações gerais e no original completo.
    footer = max((i for i, line in enumerate(lines) if line.strip() == SITE_END), default=len(lines))
    body = lines[:footer]
    after = "\n".join(lines[footer + 1:]).strip("\n") if footer < len(lines) else ""
    headers = []
    for i, line in enumerate(body):
        found = _HEADER.match(line)
        if not found:
            continue
        nxt = next((line for line in body[i + 1:] if line.strip()), "")
        # Quantidade inválida continua localizável (ex.: "Quantidade 2").
        # Uma enumeração comum na nota não vira item automaticamente.
        inside_note = bool(headers) and any(_NOTE.match(part) for part in body[headers[-1][0] + 1:i])
        separated = i == 0 or not body[i - 1].strip()
        if (_QUANTITY_LIKE.match(nxt)
                or (_NOTE.match(nxt) and (not headers or separated))
                or (not inside_note and (not headers or separated))):
            headers.append((i, int(found[1]), found[2]))
    if not headers:
        result["erros"].append("Nenhum item no formato do site foi identificado. Use linhas como '1. Nome do produto' e, em seguida, 'Quantidade: 2'.")
        return result
    if len(headers) > MAX_ITEMS:
        result["erros"].append("A mensagem tem mais de 100 itens. Divida a solicitação antes de analisar; nenhum item foi importado.")
        return result
    numbers = [number for _, number, _ in headers]
    if numbers != list(range(1, len(headers) + 1)):
        result["erros"].append("A numeração dos produtos deve começar em 1 e seguir sem repetição ou salto. Confira a mensagem e analise novamente.")

    before = "\n".join(body[:headers[0][0]]).strip("\n")
    if before.strip() == SITE_INTRO:
        before = ""
    general = "\n\n".join(part for part in (before, after) if part)
    result["observacoes_gerais"] = general
    if general:
        result["avisos"].append("Há texto adicional antes/depois da lista. Ele será preservado integralmente na mensagem de origem; cliente, datas, entrega e valores não são preenchidos a partir desse texto.")
    if any(_QUANTITY_LIKE.match(line) for line in body[:headers[0][0]]):
        result["erros"].append("Há uma quantidade antes do primeiro produto identificado. Confira se falta um item na lista.")

    for index, (start, number, name) in enumerate(headers):
        end = headers[index + 1][0] if index + 1 < len(headers) else len(body)
        block = body[start + 1:end]
        nonempty = [i for i, line in enumerate(block) if line.strip()]
        first = nonempty[0] if nonempty else None
        quantity_line = _QUANTITY.match(block[first]) if first is not None else None
        quantity = None
        warnings = []
        if quantity_line:
            try:
                quantity = _quantity(quantity_line[1])
            except ValueError as exc:
                warnings.append(f"Quantidade recebida inválida ({quantity_line[1]}): {exc} Corrija na revisão.")
        else:
            warnings.append("Quantidade ausente ou sem o formato 'Quantidade: número'. Preencha a quantidade na revisão.")
        quantity_positions = [i for i, line in enumerate(block) if _QUANTITY_LIKE.match(line)]
        if len(quantity_positions) > 1 or (quantity_positions and quantity_positions[0] != first):
            result["erros"].append(f"Item {number}: há outra linha de quantidade dentro das observações. Confira a divisão dos produtos antes de importar.")
        note_lines = block[first + 1:] if quantity_line else block
        note_nonempty = next((i for i, line in enumerate(note_lines) if line.strip()), None)
        if note_nonempty is not None:
            note_label = _NOTE.match(note_lines[note_nonempty])
            if note_label:
                note_lines = note_lines[:note_nonempty] + [note_label[1]] + note_lines[note_nonempty + 1:]
            else:
                warnings.append("Texto adicional foi mantido nas especificações. Confira sua ligação com este produto.")
        note = "\n".join(note_lines).strip("\n")
        if any(_HEADER.match(line) for line in note.splitlines()):
            warnings.append("Há uma lista numerada nas observações. Confira se algum produto ficou sem sua linha 'Quantidade:'.")
        if not name.strip():
            result["erros"].append(f"Item {number}: o nome do produto está vazio. Corrija a mensagem antes de analisar novamente.")
        matched = _match_product(name, catalogo)
        matched["avisos"] = warnings + matched["avisos"]
        result["itens"].append({
            "linha": start + 1, "numero": number, "produto_recebido": name,
            "quantidade": quantity, "quantidade_recebida": quantity_line[1] if quantity_line else "",
            "especificacoes": note, **matched,
        })
    return result


def preparar_rascunho(analise, itens_revisados, *, cliente="", whatsapp="", evento="", confirmar_sem_preco=False):
    """Valida a revisão completa e retorna somente os campos do formulário.

    Não associa clientes, não recalcula perfil comercial, não cria pedido e não
    aceita identidade comercial fornecida nos campos editados da revisão.
    """
    if not isinstance(analise, Mapping) or analise.get("erros"):
        raise ValueError("Corrija os problemas da mensagem e analise novamente antes de abrir o rascunho.")
    original = analise.get("texto_original")
    source = analise.get("itens")
    if not isinstance(original, str) or not original.strip() or len(original) > MAX_TEXT_LENGTH:
        raise ValueError("Mensagem de origem ausente ou acima do limite.")
    if not isinstance(source, list) or not 0 < len(source) <= MAX_ITEMS:
        raise ValueError("A análise não contém uma lista válida de itens.")
    if not isinstance(itens_revisados, list) or len(itens_revisados) != len(source):
        raise ValueError("Revise todas as linhas, na ordem da mensagem. Para acrescentar ou remover itens, edite a mensagem e analise novamente.")
    itens = []
    for index, (base, revised) in enumerate(zip(source, itens_revisados), 1):
        if not isinstance(base, Mapping) or not isinstance(revised, Mapping):
            raise ValueError(f"Item {index}: revisão inválida.")
        if revised.get("linha") != base.get("linha") or revised.get("produto") != base.get("produto"):
            raise ValueError(f"Item {index}: a identidade ou ordem foi alterada. Edite a mensagem e analise novamente para trocar o produto.")
        name = str(base.get("produto") or "").strip()
        if not name:
            raise ValueError(f"Item {index}: informe o produto na mensagem.")
        try:
            quantity = _quantity(revised.get("quantidade"))
            price = _price(revised.get("valor_unitario"))
        except ValueError as exc:
            raise ValueError(f"Item {index}: {exc}") from None
        if not price and confirmar_sem_preco is not True:
            raise ValueError("Há item sem preço. Informe o valor ou confirme explicitamente a abertura com itens sem preço.")
        spec = revised.get("especificacoes", "")
        if not isinstance(spec, str):
            raise ValueError(f"Item {index}: as especificações devem ser texto.")
        if len(spec) > MAX_TEXT_LENGTH:
            raise ValueError(f"Item {index}: as especificações ultrapassam 100.000 caracteres.")
        item = {field: deepcopy(base.get(field, "")) for field in _IDENTITY_FIELDS}
        item.update(produto=name, quantidade=quantity, valor_unitario=price, especificacoes=spec)
        itens.append(item)
    return {
        "cliente": str(cliente or "").strip(), "whatsapp": str(whatsapp or "").strip(),
        "evento": str(evento or "").strip(), "itens": itens,
        "observacoes": SOURCE_PREFIX + original,
    }
