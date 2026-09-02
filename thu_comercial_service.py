"""20.4.9-I8.13.5-HF16 — inteligência comercial/financeira assistida do THU.

Serviço puro, sem Streamlit/Supabase. Ele registra metadados manuais de contato
comercial/cobrança na própria proposta e monta filas assistidas usando somente a
Fonte Única de Status. Nenhuma aprovação, pagamento, encerramento ou mensagem é
feita automaticamente.
"""
from __future__ import annotations

from datetime import date, datetime
import re
from typing import Any

from proposal_status import resumo_status, valor_bool


def _parse_datetime(valor: Any) -> datetime | None:
    if isinstance(valor, datetime):
        return valor.replace(tzinfo=None)
    if isinstance(valor, date):
        return datetime(valor.year, valor.month, valor.day)
    texto = str(valor or "").strip()
    if not texto:
        return None
    texto = texto.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(texto)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except ValueError:
        pass
    for fmt in (
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(texto[:19], fmt)
        except ValueError:
            continue
    return None


def _parse_date(valor: Any) -> date | None:
    dt = _parse_datetime(valor)
    return dt.date() if dt else None


def _telefone_chave(valor: Any) -> str:
    digitos = re.sub(r"\D", "", str(valor or ""))
    if digitos.startswith("55") and len(digitos) > 11:
        digitos = digitos[2:]
    return digitos


def aplicar_registro_envio(
    proposta: dict[str, Any],
    *,
    now_text: str,
    usuario: str = "Jorge",
) -> dict[str, Any]:
    """Registra envio/retorno sem alterar status comercial da proposta.

    ``enviado_em`` guarda o primeiro registro; ``ultimo_envio_em`` guarda o
    contato mais recente. Repetir o registro é permitido e incrementa a contagem.
    """
    proposta["enviado"] = True
    if not str(proposta.get("enviado_em") or "").strip():
        proposta["enviado_em"] = str(now_text)
    proposta["ultimo_envio_em"] = str(now_text)
    proposta["enviado_por"] = str(usuario or "Jorge").strip() or "Jorge"
    try:
        anterior = int(proposta.get("envios_qtd") or 0)
    except (TypeError, ValueError):
        anterior = 0
    proposta["envios_qtd"] = anterior + 1
    return proposta


def montar_retornos_comerciais(
    historico: list[dict[str, Any]] | None,
    hoje: date,
    *,
    limite: int = 8,
) -> list[dict[str, Any]]:
    """Monta fila assistida de propostas enviadas ainda sem aprovação.

    Só entram propostas com envio explicitamente registrado. Assim o THU não
    presume que abrir/gerar um orçamento significa que ele foi realmente enviado.
    """
    saida: list[dict[str, Any]] = []
    for proposta in historico or []:
        if not isinstance(proposta, dict):
            continue
        estado = resumo_status(proposta)
        if estado.get("encerrada") or estado.get("entregue") or estado.get("aprovado"):
            continue
        if not valor_bool(proposta.get("enviado")):
            continue

        contato_dt = (
            _parse_datetime(proposta.get("ultimo_envio_em"))
            or _parse_datetime(proposta.get("enviado_em"))
            or _parse_datetime(proposta.get("data_geracao"))
            or _parse_datetime(proposta.get("data"))
        )
        dias_sem_retorno = max(0, (hoje - contato_dt.date()).days) if contato_dt else 0
        entrega = _parse_date(proposta.get("data_entrega"))
        dias_entrega = (entrega - hoje).days if entrega else None

        if dias_entrega is not None and dias_entrega < 0:
            prioridade = 1000 + min(abs(dias_entrega), 30) * 8 + min(dias_sem_retorno, 30)
            nivel = "urgente"
            motivo = f"Prazo informado venceu há {abs(dias_entrega)} dia(s) · último contato há {dias_sem_retorno} dia(s)"
            acao = "Retomar agora e confirmar se o cliente ainda deseja seguir"
        elif dias_entrega is not None and dias_entrega <= 2:
            prioridade = 900 + (2 - dias_entrega) * 20 + min(dias_sem_retorno, 30)
            nivel = "alta"
            prazo_txt = "hoje" if dias_entrega == 0 else f"em {dias_entrega} dia(s)"
            motivo = f"Prazo {prazo_txt} · último contato há {dias_sem_retorno} dia(s)"
            acao = "Retomar cliente e confirmar aprovação ou ajuste"
        elif dias_sem_retorno >= 3:
            prioridade = 800 + min(dias_sem_retorno, 30) * 4
            nivel = "alta"
            motivo = f"Sem aprovação após {dias_sem_retorno} dia(s) do último contato"
            acao = "Fazer acompanhamento comercial"
        elif dias_sem_retorno >= 1:
            prioridade = 650 + dias_sem_retorno * 4
            nivel = "normal"
            motivo = f"Aguardando retorno há {dias_sem_retorno} dia(s)"
            acao = "Retomar cliente de forma leve"
        else:
            prioridade = 300
            nivel = "aguardar"
            motivo = "Envio/retorno registrado hoje"
            acao = "Aguardar retorno do cliente"

        nome = str(proposta.get("cliente_nome") or proposta.get("cliente") or "Cliente").strip() or "Cliente"
        numero = str(proposta.get("numero_proposta") or "—").strip() or "—"
        whatsapp = str(proposta.get("whatsapp") or proposta.get("cliente_wa") or "").strip()
        mensagem = (
            f"Olá, {nome}! Passando para saber se conseguiu analisar o orçamento {numero}. "
            "Se quiser, posso tirar dúvidas ou ajustar algum detalhe."
        )
        saida.append({
            "numero_proposta": numero,
            "cliente_nome": nome,
            "whatsapp": whatsapp,
            "whatsapp_chave": _telefone_chave(whatsapp),
            "ultimo_contato_em": str(proposta.get("ultimo_envio_em") or proposta.get("enviado_em") or ""),
            "dias_sem_retorno": dias_sem_retorno,
            "data_entrega": str(proposta.get("data_entrega") or ""),
            "dias_para_entrega": dias_entrega,
            "nivel": nivel,
            "motivo": motivo,
            "acao": acao,
            "prioridade": prioridade,
            "mensagem_sugerida": mensagem,
            "envios_qtd": int(proposta.get("envios_qtd") or 1) if str(proposta.get("envios_qtd") or "1").isdigit() else 1,
        })

    saida.sort(key=lambda item: (-int(item.get("prioridade") or 0), -int(item.get("dias_sem_retorno") or 0), str(item.get("numero_proposta") or "")))
    return saida[: max(0, int(limite or 0))]


def aplicar_registro_cobranca(
    proposta: dict[str, Any],
    *,
    now_text: str,
    usuario: str = "Jorge",
) -> dict[str, Any]:
    """Registra uma cobrança realmente realizada sem alterar o status Pago.

    O registro é deliberadamente separado de ``enviado_em``: um retorno de
    orçamento não pode ser confundido com uma cobrança financeira.
    """
    proposta["cobranca_registrada"] = True
    if not str(proposta.get("primeira_cobranca_em") or "").strip():
        proposta["primeira_cobranca_em"] = str(now_text)
    proposta["ultima_cobranca_em"] = str(now_text)
    proposta["cobranca_por"] = str(usuario or "Jorge").strip() or "Jorge"
    try:
        anterior = int(proposta.get("cobrancas_qtd") or 0)
    except (TypeError, ValueError):
        anterior = 0
    proposta["cobrancas_qtd"] = anterior + 1
    return proposta


def montar_cobrancas_assistidas(
    historico: list[dict[str, Any]] | None,
    hoje: date,
    *,
    limite: int = 8,
) -> list[dict[str, Any]]:
    """Monta fila de pedidos aprovados e ainda não pagos.

    Regras de segurança:
    - mensalistas ficam fora: o pagamento deles pertence ao fechamento mensal;
    - proposta encerrada fica fora;
    - ``Pago`` continua vindo exclusivamente da Fonte Única de Status;
    - pedido entregue e não pago continua na fila financeira (a entrega encerra
      a operação, mas não apaga a pendência financeira).
    """
    saida: list[dict[str, Any]] = []
    for proposta in historico or []:
        if not isinstance(proposta, dict):
            continue
        estado = resumo_status(proposta)
        if estado.get("encerrada") or estado.get("mensalista"):
            continue
        if not estado.get("aprovado") or estado.get("pago"):
            continue

        cobranca_dt = (
            _parse_datetime(proposta.get("ultima_cobranca_em"))
            or _parse_datetime(proposta.get("primeira_cobranca_em"))
        )
        aprovacao_dt = (
            _parse_datetime(proposta.get("aprovado_em"))
            or _parse_datetime(proposta.get("data_aprovacao"))
            or _parse_datetime(proposta.get("data_geracao"))
            or _parse_datetime(proposta.get("data"))
        )
        referencia_dt = cobranca_dt or aprovacao_dt
        dias_sem_cobranca = max(0, (hoje - referencia_dt.date()).days) if referencia_dt else 0
        cobranca_ja_registrada = bool(cobranca_dt) or valor_bool(proposta.get("cobranca_registrada"))

        entrega = _parse_date(proposta.get("data_entrega"))
        dias_entrega = (entrega - hoje).days if entrega else None

        if estado.get("entregue"):
            prioridade = 1250 + min(dias_sem_cobranca, 30) * 5
            nivel = "urgente"
            motivo = f"Pedido entregue com pagamento pendente · última referência há {dias_sem_cobranca} dia(s)"
            acao = "Confirmar recebimento do pagamento ou solicitar comprovante"
        elif dias_entrega is not None and dias_entrega < 0:
            prioridade = 1150 + min(abs(dias_entrega), 30) * 8 + min(dias_sem_cobranca, 30)
            nivel = "urgente"
            motivo = f"Prazo de entrega venceu há {abs(dias_entrega)} dia(s) · pagamento ainda pendente"
            acao = "Cobrar agora e alinhar pagamento antes da conclusão da saída"
        elif estado.get("pronto"):
            prioridade = 1050 + min(dias_sem_cobranca, 30) * 4
            nivel = "alta"
            motivo = f"Pedido pronto com pagamento pendente · última referência há {dias_sem_cobranca} dia(s)"
            acao = "Confirmar pagamento antes da retirada/entrega"
        elif dias_entrega is not None and dias_entrega <= 1:
            prioridade = 980 + (1 - dias_entrega) * 20 + min(dias_sem_cobranca, 30)
            nivel = "alta"
            prazo_txt = "hoje" if dias_entrega == 0 else "amanhã"
            motivo = f"Entrega {prazo_txt} · pagamento pendente"
            acao = "Confirmar pagamento com o cliente"
        elif not cobranca_ja_registrada:
            prioridade = 780 + min(dias_sem_cobranca, 30) * 4
            nivel = "normal"
            motivo = f"Pedido aprovado e ainda sem cobrança registrada · há {dias_sem_cobranca} dia(s)"
            acao = "Enviar lembrete de pagamento e registrar a cobrança"
        elif dias_sem_cobranca >= 3:
            prioridade = 860 + min(dias_sem_cobranca, 30) * 4
            nivel = "alta"
            motivo = f"Pagamento pendente · última cobrança há {dias_sem_cobranca} dia(s)"
            acao = "Retomar cobrança"
        elif dias_sem_cobranca >= 1:
            prioridade = 690 + dias_sem_cobranca * 4
            nivel = "normal"
            motivo = f"Pagamento pendente · última cobrança há {dias_sem_cobranca} dia(s)"
            acao = "Acompanhar pagamento"
        else:
            prioridade = 320
            nivel = "aguardar"
            motivo = "Cobrança registrada hoje · pagamento ainda pendente"
            acao = "Aguardar retorno/comprovante do cliente"

        nome = str(proposta.get("cliente_nome") or proposta.get("cliente") or "Cliente").strip() or "Cliente"
        numero = str(proposta.get("numero_proposta") or "—").strip() or "—"
        whatsapp = str(proposta.get("whatsapp") or proposta.get("cliente_wa") or "").strip()
        mensagem = (
            f"Olá, {nome}! Sobre o pedido {numero}, consta o pagamento pendente. "
            "Se já realizou, pode me enviar o comprovante, por favor? "
            "Se precisar, envio novamente os dados do PIX."
        )
        saida.append({
            "numero_proposta": numero,
            "cliente_nome": nome,
            "whatsapp": whatsapp,
            "whatsapp_chave": _telefone_chave(whatsapp),
            "ultima_cobranca_em": str(proposta.get("ultima_cobranca_em") or proposta.get("primeira_cobranca_em") or ""),
            "cobranca_registrada": cobranca_ja_registrada,
            "dias_sem_cobranca": dias_sem_cobranca,
            "data_entrega": str(proposta.get("data_entrega") or ""),
            "dias_para_entrega": dias_entrega,
            "pronto": bool(estado.get("pronto")),
            "entregue": bool(estado.get("entregue")),
            "nivel": nivel,
            "motivo": motivo,
            "acao": acao,
            "prioridade": prioridade,
            "mensagem_sugerida": mensagem,
            "cobrancas_qtd": int(proposta.get("cobrancas_qtd") or 0) if str(proposta.get("cobrancas_qtd") or "0").isdigit() else 0,
        })

    saida.sort(
        key=lambda item: (
            -int(item.get("prioridade") or 0),
            -int(item.get("dias_sem_cobranca") or 0),
            str(item.get("numero_proposta") or ""),
        )
    )
    return saida[: max(0, int(limite or 0))]


def montar_agenda_executiva(
    retornos: list[dict[str, Any]] | None,
    cobrancas: list[dict[str, Any]] | None,
    prioridades_operacionais: list[dict[str, Any]] | None,
    sinais_continuidade: list[dict[str, Any]] | None = None,
    *,
    limite: int = 8,
) -> list[dict[str, Any]]:
    """Consolida as filas assistidas do THU em uma agenda única por proposta.

    A agenda é **somente leitura**. Ela não cria status, não registra contato e
    não altera nenhuma proposta. A mesma proposta pode ter mais de um sinal
    (por exemplo, atraso operacional + pagamento pendente), mas aparece uma só
    vez na agenda. O sinal de maior urgência vira a ação principal e os demais
    permanecem visíveis como contexto secundário.

    Entradas ``aguardar`` e pedidos operacionais ``dentro_prazo`` não entram na
    agenda executiva para evitar transformar acompanhamento passivo em tarefa.

    HF24 incorpora também os sinais de continuidade da HF21. Esse sinal nunca
    altera o pedido e, quando a mesma proposta já possui uma urgência operacional
    mais forte, aparece apenas como contexto secundário.
    """
    agrupados: dict[str, dict[str, Any]] = {}

    def _adicionar_sinal(
        item: dict[str, Any],
        *,
        dominio: str,
        icone: str,
        score: int,
        janela: str,
        motivo: str,
        acao: str,
        origem: str,
    ) -> None:
        numero = str(item.get("numero_proposta") or "").strip()
        if not numero:
            return
        cliente = str(item.get("cliente_nome") or item.get("cliente") or "Cliente").strip() or "Cliente"
        grupo = agrupados.setdefault(
            numero,
            {
                "numero_proposta": numero,
                "cliente_nome": cliente,
                "sinais": [],
            },
        )
        if not str(grupo.get("cliente_nome") or "").strip() or grupo.get("cliente_nome") == "Cliente":
            grupo["cliente_nome"] = cliente
        grupo["sinais"].append({
            "dominio": dominio,
            "icone": icone,
            "score": int(score),
            "janela": janela,
            "motivo": str(motivo or "").strip(),
            "acao": str(acao or "").strip(),
            "origem": origem,
            "whatsapp": str(item.get("whatsapp") or "").strip(),
            "whatsapp_chave": str(item.get("whatsapp_chave") or "").strip(),
            "mensagem_sugerida": str(item.get("mensagem_sugerida") or "").strip(),
        })

    for item in retornos or []:
        if not isinstance(item, dict):
            continue
        nivel = str(item.get("nivel") or "normal").strip().casefold()
        if nivel == "aguardar":
            continue
        janela = "agora" if nivel == "urgente" else "hoje" if nivel == "alta" else "acompanhar"
        _adicionar_sinal(
            item,
            dominio="Comercial",
            icone="💬",
            score=int(item.get("prioridade") or 0),
            janela=janela,
            motivo=str(item.get("motivo") or "Retorno comercial pendente"),
            acao=str(item.get("acao") or "Retomar cliente"),
            origem="retorno",
        )

    for item in cobrancas or []:
        if not isinstance(item, dict):
            continue
        nivel = str(item.get("nivel") or "normal").strip().casefold()
        if nivel == "aguardar":
            continue
        janela = "agora" if nivel == "urgente" else "hoje" if nivel == "alta" else "acompanhar"
        _adicionar_sinal(
            item,
            dominio="Financeiro",
            icone="💳",
            score=int(item.get("prioridade") or 0) + 40,
            janela=janela,
            motivo=str(item.get("motivo") or "Pagamento pendente"),
            acao=str(item.get("acao") or "Acompanhar pagamento"),
            origem="cobranca",
        )

    # HF24 — incorpora o radar de continuidade à ordem executiva. O score já
    # nasce calibrado no serviço da HF21: prazo vencido/hoje pode exigir ação
    # imediata; permanência recorrente com prazo futuro entra como hoje/acompanhar.
    # Como os atrasos operacionais rank 0/1 usam 1600/1400, a continuidade não
    # substitui a causa operacional mais concreta quando ambas coexistem.
    for item in sinais_continuidade or []:
        if not isinstance(item, dict):
            continue
        nivel = str(item.get("nivel") or "normal").strip().casefold()
        janela = "agora" if nivel == "urgente" else "hoje" if nivel == "alta" else "acompanhar"
        _adicionar_sinal(
            item,
            dominio="Sem avanço",
            icone="⏳",
            score=int(item.get("prioridade") or 0),
            janela=janela,
            motivo=str(item.get("motivo") or "Sem mudança de status registrada"),
            acao=str(item.get("acao") or "Abrir o pedido e conferir o próximo passo"),
            origem="continuidade",
        )

    score_por_rank = {0: 1600, 1: 1400, 2: 1120, 3: 820, 4: 520}
    for item in prioridades_operacionais or []:
        if not isinstance(item, dict):
            continue
        try:
            rank = int(item.get("prioridade_rank", 9))
        except (TypeError, ValueError):
            rank = 9
        chave = str(item.get("prioridade_chave") or "").strip()
        if rank > 4 or chave == "dentro_prazo":
            continue
        janela = "agora" if rank <= 1 else "hoje" if rank == 2 else "acompanhar"
        area = str(item.get("area") or "Produção").strip() or "Produção"
        icone = "🚚" if area.casefold() == "entrega" else "🏭"
        _adicionar_sinal(
            item,
            dominio=area,
            icone=icone,
            score=score_por_rank.get(rank, 0),
            janela=janela,
            motivo=str(item.get("motivo_prioridade") or item.get("prioridade_rotulo") or "Atenção operacional"),
            acao=str(item.get("proxima_acao") or "Revisar pedido"),
            origem="operacao",
        )

    agenda: list[dict[str, Any]] = []
    ordem_janela = {"agora": 0, "hoje": 1, "acompanhar": 2}
    for numero, grupo in agrupados.items():
        sinais = list(grupo.get("sinais") or [])
        if not sinais:
            continue
        sinais.sort(
            key=lambda s: (
                -int(s.get("score") or 0),
                ordem_janela.get(str(s.get("janela") or "acompanhar"), 9),
                str(s.get("dominio") or ""),
            )
        )
        principal = sinais[0]
        agenda.append({
            "numero_proposta": numero,
            "cliente_nome": grupo.get("cliente_nome") or "Cliente",
            "prioridade_score": int(principal.get("score") or 0),
            "janela": principal.get("janela") or "acompanhar",
            "dominio": principal.get("dominio") or "Operação",
            "icone": principal.get("icone") or "📌",
            "motivo": principal.get("motivo") or "Atenção necessária",
            "acao": principal.get("acao") or "Revisar pedido",
            "origem": principal.get("origem") or "operacao",
            "whatsapp": principal.get("whatsapp") or "",
            "whatsapp_chave": principal.get("whatsapp_chave") or "",
            "mensagem_sugerida": principal.get("mensagem_sugerida") or "",
            "sinais": sinais,
            "sinais_qtd": len(sinais),
            "dominios_secundarios": [
                f"{s.get('icone', '📌')} {s.get('dominio', 'Outro')}"
                for s in sinais[1:]
            ],
        })

    agenda.sort(
        key=lambda item: (
            ordem_janela.get(str(item.get("janela") or "acompanhar"), 9),
            -int(item.get("prioridade_score") or 0),
            str(item.get("cliente_nome") or "").casefold(),
            str(item.get("numero_proposta") or ""),
        )
    )
    return agenda[: max(0, int(limite or 0))]

