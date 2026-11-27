"""HF57: rascunho portátil de orçamento, sem arquivos, rede ou persistência.

O documento contém somente campos do formulário e referências informativas.
Importar não autoriza gravar, restaurar status ou editar uma proposta existente.
Pendências são listas de referências para recuperação manual: nunca viram itens
ou widgets ativos. Captura somente valores já presentes no estado; texto de um
st.form ainda não enviado pelo navegador não pode ser recuperado aqui.

Limites: 2 MiB de UTF-8, 1.000 itens, 100.000 caracteres por texto (inclusive
chaves), profundidade 12 com a raiz em 1, 40.000 objetos/listas/valores e 50
pendências de cada tipo. Chaves não somam nós. Nenhum limite trunca conteúdo.
Todas as entradas inválidas produzem ValueError com mensagem para a interface.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import date, datetime
import hashlib
import json
import math
import re

from manager_workflow_hf53 import QUOTE_FIELDS, item_em_preenchimento


SCHEMA = "alphafest.rascunho_orcamento"
SCHEMA_VERSION = 1
MAX_BYTES = 2 * 1024 * 1024
MAX_ITEMS = 1_000
MAX_TEXT = 100_000
MAX_DEPTH = 12
MAX_NODES = 40_000
MAX_PENDING = 50

_ROOT_KEYS = {"schema", "schema_version", "manager_version", "criado_em",
              "origem", "formulario", "pendencias"}
_ORIGIN_KEYS = {"perfil", "numero_proposta", "atendimento_id", "projeto_id"}
_PENDING_KEYS = {"item_nao_adicionado", "edicao_item"}
_FORM_KEYS = set(QUOTE_FIELDS) | {"itens"}
_TEXT_FIELDS = set(QUOTE_FIELDS) - {"desconto", "taxa_entrega", "entrega", "frete"}
_ITEM_KEYS = {"produto", "especificacoes", "quantidade", "valor_unitario"}
_PENDING_ITEM_KEYS = {"perfil", "sequencia", "produto_catalogo", "produto_livre",
                      "quantidade", "valor_unitario", "detalhes"}
_EDITOR_KEYS = {"indice", "original", "campos"}


def _erro(path, reason):
    raise ValueError(f"Rascunho inválido: {path} {reason}")


def _campo(path, key):
    # Caminhos ajudam a corrigir o arquivo sem reproduzir textos sensíveis.
    return f"{path}.{key}" if len(key) <= 60 and key.isprintable() else f"{path}.[campo]"


def _texto(value, path):
    if not isinstance(value, str):
        _erro(path, "deve ser texto.")
    if len(value) > MAX_TEXT:
        _erro(path, f"ultrapassa {MAX_TEXT:,} caracteres.".replace(",", "."))
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeError:
        _erro(path, "contém Unicode inválido; use texto UTF-8 válido.")


def _numero(value, path, *, nao_negativo=False, exato_float=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _erro(path, "deve ser um número finito, sem texto ou valor booleano.")
    try:
        finite = math.isfinite(value)
    except (OverflowError, ValueError):
        finite = False
    if not finite:
        _erro(path, "deve ser um número finito representável no formulário.")
    if nao_negativo and value < 0:
        _erro(path, "não pode ser negativo.")
    if exato_float and isinstance(value, int) and float(value) != value:
        _erro(path, "não pode ser representado exatamente pelo campo numérico do formulário. Revise o valor antes de recuperar o rascunho.")


def _inteiro(value, path):
    if type(value) is not int or value < 0:
        _erro(path, "deve ser um inteiro maior ou igual a zero.")


def _objeto(value, keys, path):
    if not isinstance(value, dict) or set(value) != set(keys):
        _erro(path, "possui campos ausentes, desconhecidos ou formato incompatível.")


def _arvore_json(value):
    """Confere toda a árvore, inclusive metadados desconhecidos, sem recursão."""
    stack = [(value, "documento", 1, frozenset())]
    count = 0
    while stack:
        current, path, depth, ancestors = stack.pop()
        count += 1
        if count > MAX_NODES:
            _erro("documento", f"ultrapassa o limite de {MAX_NODES:,} nós.".replace(",", "."))
        if depth > MAX_DEPTH:
            _erro(path, f"ultrapassa a profundidade máxima de {MAX_DEPTH} níveis.")
        if current is None or isinstance(current, bool):
            continue
        if isinstance(current, str):
            _texto(current, path)
        elif isinstance(current, (int, float)):
            _numero(current, path)
        elif isinstance(current, (dict, list)):
            if id(current) in ancestors:
                _erro(path, "contém uma referência circular.")
            if len(current) > MAX_NODES - count:
                _erro("documento", f"ultrapassa o limite de {MAX_NODES:,} nós.".replace(",", "."))
            parents = ancestors | {id(current)}
            if isinstance(current, dict):
                for key, child in current.items():
                    _texto(key, f"{path}.[nome de campo]")
                    stack.append((child, _campo(path, key), depth + 1, parents))
            else:
                stack.extend((child, f"{path}[{index}]", depth + 1, parents)
                             for index, child in enumerate(current))
        else:
            _erro(path, "contém um tipo que não pertence ao formato JSON.")


def _data_iso(value, path):
    if value is None:
        return
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        _erro(path, "deve ser uma data ISO (aaaa-mm-dd) ou nulo.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        _erro(path, "contém uma data inexistente.")
    # Os date_input atuais calculam limites em valor ± 10 anos; a leitura
    # desses limites requer quatro dígitos para o ano. Abaixo de 1010 ou acima
    # de 9989, uma data ISO válida pode impedir a abertura do formulário.
    if not 1010 <= parsed.year <= 9989:
        _erro(path, "deve ter ano entre 1010 e 9989 para abrir no formulário atual.")


def _instante_iso(value, path):
    if not isinstance(value, str) or not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})", value):
        _erro(path, "deve ser uma data e hora ISO com fuso horário.")
    try:
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if instant.utcoffset() is None:
            raise ValueError
    except ValueError:
        _erro(path, "contém data, hora ou fuso horário inválido.")


def _origem(value, path="origem"):
    _objeto(value, _ORIGIN_KEYS, path)
    if value["perfil"] not in ("jorge", "anna"):
        _erro(path + ".perfil", "deve identificar Jorge ou Anna.")
    for key in _ORIGIN_KEYS - {"perfil"}:
        _texto(value[key], path + "." + key)


def _item(value, path):
    if not isinstance(value, dict) or not _ITEM_KEYS <= set(value):
        _erro(path, "deve conter produto, especificacoes, quantidade e valor_unitario.")
    _texto(value["produto"], path + ".produto")
    _texto(value["especificacoes"], path + ".especificacoes")
    _numero(value["quantidade"], path + ".quantidade", exato_float=True)
    _numero(value["valor_unitario"], path + ".valor_unitario", exato_float=True)


def _pendencias(value, path="pendencias"):
    _objeto(value, _PENDING_KEYS, path)
    for kind in _PENDING_KEYS:
        entries = value[kind]
        if not isinstance(entries, list) or len(entries) > MAX_PENDING:
            _erro(path + "." + kind, f"deve ser uma lista com até {MAX_PENDING} referências manuais.")
        for index, entry in enumerate(entries):
            location = f"{path}.{kind}[{index}]"
            if kind == "item_nao_adicionado":
                _objeto(entry, _PENDING_ITEM_KEYS, location)
                if entry["perfil"] not in ("jorge", "anna"):
                    _erro(location + ".perfil", "deve identificar Jorge ou Anna.")
                _inteiro(entry["sequencia"], location + ".sequencia")
                for name in ("produto_catalogo", "produto_livre"):
                    _texto(entry[name], location + "." + name)
                for name in ("quantidade", "valor_unitario"):
                    _numero(entry[name], location + "." + name, exato_float=True)
                detail_keys = {"tema", "nome_item", "cor", "idade", "obs" if entry["perfil"] == "anna" else "obs_item"}
                _objeto(entry["detalhes"], detail_keys, location + ".detalhes")
                for name in detail_keys:
                    _texto(entry["detalhes"][name], location + ".detalhes." + name)
            else:
                _objeto(entry, _EDITOR_KEYS, location)
                _inteiro(entry["indice"], location + ".indice")
                _item(entry["original"], location + ".original")
                _objeto(entry["campos"], _ITEM_KEYS, location + ".campos")
                _item(entry["campos"], location + ".campos")


def _validar(documento):
    _arvore_json(documento)
    _objeto(documento, _ROOT_KEYS, "documento")
    if documento["schema"] != SCHEMA:
        _erro("schema", "não identifica um rascunho de orçamento AlphaFest.")
    if type(documento["schema_version"]) is not int or documento["schema_version"] != SCHEMA_VERSION:
        _erro("schema_version", "não é uma versão de rascunho suportada por este Manager.")
    _texto(documento["manager_version"], "manager_version")
    _instante_iso(documento["criado_em"], "criado_em")
    _origem(documento["origem"])
    form = documento["formulario"]
    _objeto(form, _FORM_KEYS, "formulario")
    for field in _TEXT_FIELDS:
        _texto(form[field], "formulario." + field)
    for field in ("desconto", "taxa_entrega"):
        _numero(form[field], "formulario." + field, nao_negativo=True, exato_float=True)
    if form["frete"] not in ("Entrega", "Retirada"):
        _erro("formulario.frete", "deve ser Entrega ou Retirada.")
    _data_iso(form["entrega"], "formulario.entrega")
    if not isinstance(form["itens"], list) or len(form["itens"]) > MAX_ITEMS:
        _erro("formulario.itens", f"deve ser uma lista com até {MAX_ITEMS:,} itens.".replace(",", "."))
    for index, item in enumerate(form["itens"]):
        _item(item, f"formulario.itens[{index}]")
    _pendencias(documento["pendencias"])
    try:
        raw = json.dumps(documento, ensure_ascii=False, allow_nan=False,
                         sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError, UnicodeError):
        _erro("documento", "não pode ser representado integralmente em JSON UTF-8.")
    if len(raw) > MAX_BYTES:
        _erro("documento", "ultrapassa o limite de 2 MiB. Nenhum conteúdo foi cortado.")
    return raw


def _referencia(value, path):
    if value is None:
        return ""
    _texto(value, path)
    return value


def _capturar_item_pendente(estado, anna):
    try:
        pending = item_em_preenchimento(estado, anna=anna)
    except (TypeError, ValueError, OverflowError, RecursionError):
        _erro("item em preenchimento", "contém valores incompatíveis com o formulário.")
    if pending is None:
        return None
    # O helper reconhece a geração ativa. O arquivo preserva o texto exato dos
    # campos confirmados, inclusive espaços, em vez do texto aparado da prévia.
    sequence = pending["sequencia"]
    prefix = "anna_modal_" if anna else ""
    product = f"anna_modal_prod_{sequence}" if anna else f"produto_novo_{sequence}"
    for field, suffix in (("produto_catalogo", "_catalogo"), ("produto_livre", "_livre")):
        pending[field] = estado.get(product + suffix, "")
    for field in pending["detalhes"]:
        pending["detalhes"][field] = estado.get(f"{prefix}{field}_{sequence}", "")
    return pending


def _capturar_edicao(estado, perfil):
    editing = estado.get("_hf53_edicao_" + perfil)
    if editing is None:
        return None
    if not isinstance(editing, Mapping) or not {"indice", "original", "token"} <= set(editing):
        _erro("edição de item", "não contém uma referência de edição válida.")
    _inteiro(editing["token"], "edição de item.token")
    original = editing["original"]
    _item(original, "edição de item.original")
    prefix = f"hf53_item_{perfil}_{editing['token']}"
    fields = {field: estado.get(prefix + "_" + widget, original[field])
              for field, widget in (("produto", "produto"), ("especificacoes", "especificacoes"),
                                    ("quantidade", "quantidade"), ("valor_unitario", "valor"))}
    return {"indice": editing["indice"], "original": original, "campos": fields}


def capturar_rascunho(estado, *, anna=False, agora, versao_manager):
    """Captura somente a whitelist do perfil, sem alterar estado ou consultar hora."""
    if not isinstance(estado, Mapping):
        _erro("estado do formulário", "deve ser um mapeamento de campos.")
    perfil, prefix = ("anna", "anna_modal_") if anna else ("jorge", "form_")
    defaults = {field: "" for field in _TEXT_FIELDS}
    defaults.update(desconto=0.0, taxa_entrega=0.0, entrega=None, frete="Retirada")
    form = {field: estado.get(prefix + field, defaults[field]) for field in QUOTE_FIELDS}
    # Antes do primeiro item, Jorge ainda usa o rótulo legado da empresa.
    # A modalidade do seletor é Retirada; o estado original não é alterado.
    if form["frete"] == "Retirada em Itatiba":
        form["frete"] = "Retirada"
    delivery = form["entrega"]
    if isinstance(delivery, datetime):
        form["entrega"] = delivery.date().isoformat()
    elif isinstance(delivery, date):
        form["entrega"] = delivery.isoformat()
    form["itens"] = estado.get("anna_modal_itens" if anna else "temp_itens", [])
    origin_prefix = "_anna_hf53" if anna else ""
    origin = {
        "perfil": perfil,
        "numero_proposta": _referencia(estado.get("anna_modal_numero_original" if anna else "editar_numero"), "origem.numero_proposta"),
        "atendimento_id": _referencia(estado.get(origin_prefix + "_atendimento_origem_id"), "origem.atendimento_id"),
        "projeto_id": _referencia(estado.get(origin_prefix + "_projeto_origem_id"), "origem.projeto_id"),
    }
    recovered_origin = estado.get("_hf57_origem_rascunho_" + perfil)
    if recovered_origin is not None:
        _objeto(recovered_origin, _ORIGIN_KEYS | {"criado_em", "manager_version"}, "origem recuperada")
        _origem({key: recovered_origin[key] for key in _ORIGIN_KEYS}, "origem recuperada")
        _instante_iso(recovered_origin["criado_em"], "origem recuperada.criado_em")
        _texto(recovered_origin["manager_version"], "origem recuperada.manager_version")
        if not any(origin[key] for key in _ORIGIN_KEYS - {"perfil"}):
            origin = {key: recovered_origin[key] for key in _ORIGIN_KEYS}

    recovered = estado.get("_hf57_pendencias_rascunho_" + perfil)
    if recovered is None:
        recovered = {key: [] for key in _PENDING_KEYS}
    _arvore_json(recovered)
    _pendencias(recovered, "pendências recuperadas")
    pending = {key: list(recovered[key]) for key in _PENDING_KEYS}
    local = {"item_nao_adicionado": _capturar_item_pendente(estado, anna),
             "edicao_item": _capturar_edicao(estado, perfil)}
    for key in _PENDING_KEYS:
        candidates = pending[key] + ([local[key]] if local[key] is not None else [])
        # A validação vem antes da serialização para evitar coerções silenciosas.
        _arvore_json(candidates)
        seen = set()
        pending[key] = []
        for candidate in candidates:
            canonical = json.dumps(candidate, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":"))
            if canonical not in seen:
                seen.add(canonical)
                pending[key].append(candidate)

    document = {"schema": SCHEMA, "schema_version": SCHEMA_VERSION,
                "manager_version": versao_manager,
                "criado_em": agora.isoformat() if isinstance(agora, datetime) else agora,
                "origem": origin, "formulario": form, "pendencias": pending}
    _validar(document)
    return deepcopy(document)


def exportar_rascunho(documento) -> bytes:
    """Produz JSON UTF-8 integral. Entrada inválida não modifica o documento."""
    return _validar(documento)


def _pares_unicos(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _erro("JSON", "contém uma chave duplicada; não é seguro escolher um dos valores.")
        result[key] = value
    return result


def _constante_invalida(_):
    _erro("JSON", "contém NaN ou infinito; todos os números precisam ser finitos.")


def importar_rascunho(conteudo: bytes | str):
    """Decodifica e valida dados; nunca abre arquivos nem executa instruções."""
    if not isinstance(conteudo, (bytes, str)):
        _erro("arquivo", "deve conter bytes ou texto JSON UTF-8.")
    if len(conteudo) > MAX_BYTES:
        _erro("arquivo", "ultrapassa o limite de 2 MiB. Nenhum conteúdo foi importado.")
    try:
        raw = conteudo.encode("utf-8", errors="strict") if isinstance(conteudo, str) else conteudo
        if len(raw) > MAX_BYTES:
            _erro("arquivo", "ultrapassa o limite de 2 MiB. Nenhum conteúdo foi importado.")
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError:
        _erro("arquivo", "não contém UTF-8 válido.")
    try:
        document = json.loads(text, object_pairs_hook=_pares_unicos, parse_constant=_constante_invalida)
    except json.JSONDecodeError:
        _erro("arquivo", "não contém JSON válido; use o arquivo de rascunho exportado pelo Manager.")
    except RecursionError:
        _erro("arquivo", f"ultrapassa a profundidade máxima de {MAX_DEPTH} níveis.")
    except (ValueError, OverflowError) as error:
        if isinstance(error, ValueError) and str(error).startswith("Rascunho inválido:"):
            raise
        _erro("arquivo", "contém números ou estrutura fora dos limites permitidos.")
    _validar(document)
    return document


def assinatura_rascunho(documento) -> str:
    """Assina todo o conteúdo, exceto os dois metadados temporais do envelope."""
    _validar(documento)
    content = {key: value for key, value in documento.items() if key not in {"criado_em", "manager_version"}}
    raw = json.dumps(content, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def preparar_retomada(documento):
    """Prepara exclusivamente um NOVO orçamento para o workflow HF53.

    Origem e pendências seguem como referências sem autoridade operacional.
    Nenhum número anterior, vínculo ativo, status ou aceite é restaurado.
    """
    _validar(documento)
    result = deepcopy(documento["formulario"])
    result["entrega"] = date.fromisoformat(result["entrega"]) if result["entrega"] is not None else None
    result["_hf57_retomada"] = True
    result["_hf57_origem"] = {**deepcopy(documento["origem"]),
                              "criado_em": documento["criado_em"], "manager_version": documento["manager_version"]}
    result["_hf57_pendencias"] = deepcopy(documento["pendencias"])
    return result
