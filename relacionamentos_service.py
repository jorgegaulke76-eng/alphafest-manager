"""20.4.9-I8.13.5-HF7 — regras puras de Clientes, Relacionamentos e Pós-venda.

Este módulo não conhece Streamlit, Supabase ou session_state. Ele concentra
somente regras determinísticas de identidade/vínculo e próxima ação. A leitura
e a persistência continuam no AlphaFest Manager.

Regras preservadas:
- documento vence na identidade comercial; depois WhatsApp; depois nome;
- vínculo histórico prioriza relacionamento_id já gravado;
- dados atuais do cadastro podem atualizar somente a visão do cliente, nunca
  itens, valores, datas ou status históricos da proposta;
- propostas do cliente aceitam vínculo por id e fallback pela chave legada;
- pedido Entregue leva a pós-venda; status oficiais continuam na proposta.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

from proposal_status import resumo_status


def normalizar_texto_cliente(valor: Any) -> str:
    return re.sub(r"\s+", " ", str(valor or "").strip())


def digitos(valor: Any) -> str:
    return re.sub(r"\D", "", str(valor or ""))


def telefone_chave(valor: Any) -> str:
    numeros = digitos(valor)
    return numeros[-11:] if len(numeros) >= 11 else numeros


def chave_cliente(nome: Any, documento: Any = "", whatsapp: Any = "") -> str:
    documento_limpo = digitos(documento)
    whatsapp_limpo = digitos(whatsapp)
    if documento_limpo:
        return f"doc:{documento_limpo}"
    if whatsapp_limpo:
        return f"wa:{whatsapp_limpo}"
    return f"nome:{normalizar_texto_cliente(nome).lower()}"


def valor_preenchido(valor: Any) -> bool:
    if isinstance(valor, (list, dict)):
        return bool(valor)
    return bool(str(valor or "").strip())


def pontuacao_cadastro_relacionamento(cliente: dict[str, Any] | None) -> int:
    """Prioriza o cadastro manual/mais completo ao consolidar duplicidades."""
    cliente = cliente or {}
    campos = ["documento", "whatsapp", "email", "cidade", "aniversario", "observacoes", "segmentos", "interesses", "papeis"]
    pontos = sum(1 for campo in campos if valor_preenchido(cliente.get(campo)))
    origem = str(cliente.get("origem", cliente.get("origem_cliente", ""))).casefold()
    if "histórico" not in origem and "historico" not in origem:
        pontos += 3
    if cliente.get("politica_atendimento"):
        pontos += 2
    if cliente.get("classificacao_relacionamento") not in (None, "", "Não classificado"):
        pontos += 1
    return pontos


def localizar_cliente_comercial(
    clientes: Iterable[dict[str, Any]] | None,
    *,
    nome: Any = "",
    documento: Any = "",
    whatsapp: Any = "",
) -> dict[str, Any] | None:
    """Localiza o cadastro mestre com a mesma precedência comercial histórica."""
    lista = [c for c in (clientes or []) if isinstance(c, dict)]
    doc = digitos(documento)
    wa = telefone_chave(whatsapp)
    nome_norm = normalizar_texto_cliente(nome).casefold()
    if doc:
        achado = next((c for c in lista if digitos(c.get("documento")) == doc), None)
        if achado:
            return achado
    if wa:
        achado = next((c for c in lista if telefone_chave(c.get("whatsapp")) == wa), None)
        if achado:
            return achado
    if nome_norm:
        return next((c for c in lista if normalizar_texto_cliente(c.get("nome")).casefold() == nome_norm), None)
    return None


def localizar_relacionamento(
    clientes: Iterable[dict[str, Any]] | None,
    *,
    nome: Any = "",
    whatsapp: Any = "",
) -> dict[str, Any] | None:
    """Vínculo relacional legado: WhatsApp primeiro e nome como fallback."""
    lista = [c for c in (clientes or []) if isinstance(c, dict)]
    chave_wa = telefone_chave(whatsapp)
    nome_norm = normalizar_texto_cliente(nome).casefold()
    for cli in lista:
        if chave_wa and telefone_chave(cli.get("whatsapp")) == chave_wa:
            return cli
        if nome_norm and normalizar_texto_cliente(cli.get("nome")).casefold() == nome_norm:
            return cli
    return None


def relacionamento_da_proposta(
    proposta: dict[str, Any] | None,
    clientes: Iterable[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    """Resolve o cadastro atual priorizando relacionamento_id já persistido."""
    proposta = proposta or {}
    lista = [c for c in (clientes or []) if isinstance(c, dict)]
    rel_id = str(proposta.get("relacionamento_id", "") or "").strip()
    if rel_id:
        encontrado = next((c for c in lista if str(c.get("id", "") or "").strip() == rel_id), None)
        if encontrado:
            return encontrado
    return localizar_relacionamento(
        lista,
        nome=proposta.get("cliente_nome", proposta.get("cliente", "")),
        whatsapp=proposta.get("whatsapp", proposta.get("cliente_wa", "")),
    )


def proposta_com_dados_atuais(
    proposta: dict[str, Any] | None,
    clientes: Iterable[dict[str, Any]] | None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Monta visão atual do contato sem alterar dados históricos do pedido."""
    proposta = proposta or {}
    atual = relacionamento_da_proposta(proposta, clientes)
    if not atual:
        return dict(proposta), None
    visao = dict(proposta)
    nome = atual.get("nome") or visao.get("cliente_nome", visao.get("cliente", ""))
    documento = atual.get("documento") or visao.get("documento", visao.get("cliente_cpf_cnpj", ""))
    whatsapp = atual.get("whatsapp") or visao.get("whatsapp", visao.get("cliente_wa", ""))
    visao.update({
        "cliente_nome": nome,
        "cliente": nome,
        "documento": documento,
        "cliente_cpf_cnpj": documento,
        "whatsapp": whatsapp,
        "cliente_wa": whatsapp,
        "email": atual.get("email", visao.get("email", "")),
        "cidade": atual.get("cidade", visao.get("cidade", "")),
        "relacionamento_id": atual.get("id", visao.get("relacionamento_id", "")),
    })
    return visao, atual


def propostas_do_cliente(
    cliente: dict[str, Any] | None,
    historico: Iterable[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    cliente = cliente or {}
    rel_id = str(cliente.get("id", "") or "").strip()
    chave = chave_cliente(cliente.get("nome"), cliente.get("documento"), cliente.get("whatsapp"))
    propostas: list[dict[str, Any]] = []
    for prop in (historico or []):
        if not isinstance(prop, dict):
            continue
        if rel_id and str(prop.get("relacionamento_id", "") or "").strip() == rel_id:
            propostas.append(prop)
            continue
        pchave = chave_cliente(
            prop.get("cliente_nome", prop.get("cliente", "")),
            prop.get("documento", prop.get("cliente_cpf_cnpj", "")),
            prop.get("whatsapp", prop.get("cliente_wa", "")),
        )
        if pchave == chave:
            propostas.append(prop)
    return propostas


def proxima_acao_crm(item: dict[str, Any] | None, fallback: str = "") -> str:
    item = item or {}
    status = str(item.get("status", "Novo contato"))
    mapa = {
        "Novo contato": "Responder e entender a necessidade",
        "Catálogo solicitado": "Enviar o catálogo adequado",
        "Catálogo enviado": "Perguntar o que mais interessou",
        "Orçamento solicitado": "Preparar orçamento",
        "Orçamento em elaboração": "Finalizar e enviar orçamento",
        "Aguardando cliente": "Fazer acompanhamento",
        "Pedido aprovado": "Confirmar dados e enviar à produção",
        "Comprovante recebido": "Conferir pagamento",
        "Arte aprovada": "Iniciar produção",
        "Em produção": "Acompanhar prazo",
        "Pronto": "Avisar cliente",
        "Entregue": "Fazer pós-venda",
        "Pós-venda": "Registrar retorno e oportunidade futura",
        "Arquivado": "Sem ação",
    }
    return mapa.get(status, str(fallback or ""))


def proxima_acao_proposta(proposta: dict[str, Any] | None) -> str:
    """Próxima ação operacional/relacional usando a Fonte Única de Status."""
    proposta = proposta or {}
    estado = resumo_status(proposta)
    if estado.get("entregue"):
        return "Registrar pós-venda"
    if estado.get("encerrada"):
        return "Pedido encerrado — consultar Histórico"
    if estado.get("pronto"):
        return "Confirmar retirada/entrega"
    if estado.get("aprovado"):
        if not estado.get("pago") and not estado.get("mensalista"):
            return "Confirmar pagamento e acompanhar produção"
        return "Acompanhar produção e entrega"
    if proposta.get("enviado", False):
        return "Aguardar ou registrar aprovação do cliente"
    return "Revisar e enviar orçamento"
