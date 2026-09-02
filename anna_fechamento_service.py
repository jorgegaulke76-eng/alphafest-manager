"""20.4.9-I8.13.5-HF19 — fechamento diário comparativo da Anna.

Camada de leitura/comparação. O único dado novo persistido pela interface é uma
fotografia compacta da agenda no início do dia. Nenhum status de proposta é
alterado por este módulo.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable

from anna_agenda_service import montar_agenda_anna
from proposal_status import proposta_encerrada, resumo_status


SNAPSHOT_VERSION = 1


def criar_snapshot_inicio(
    linhas: Iterable[dict[str, Any]] | None,
    registrado_em: datetime | None = None,
) -> dict[str, Any]:
    """Cria uma fotografia serializável e compacta da agenda da manhã."""
    registrado_em = registrado_em or datetime.now()
    compactas: list[dict[str, Any]] = []
    for linha in linhas or []:
        if not isinstance(linha, dict):
            continue
        compactas.append({
            "numero_proposta": str(linha.get("numero_proposta") or "—").strip() or "—",
            "status": str(linha.get("status") or "—").strip() or "—",
            "cliente_nome": str(linha.get("cliente_nome") or "Cliente").strip() or "Cliente",
            "telefone": str(linha.get("telefone") or "—").strip() or "—",
            "produtos": str(linha.get("produtos") or "—").strip() or "—",
            "data_entrega": str(linha.get("data_entrega") or "—").strip() or "—",
        })
    return {
        "versao": SNAPSHOT_VERSION,
        "registrado_em": registrado_em.isoformat(timespec="seconds"),
        "linhas": compactas,
    }


def snapshot_valido(snapshot: Any) -> bool:
    return (
        isinstance(snapshot, dict)
        and isinstance(snapshot.get("linhas"), list)
        and bool(str(snapshot.get("registrado_em") or "").strip())
    )


def _indice_propostas(propostas: Iterable[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    indice: dict[str, dict[str, Any]] = {}
    for proposta in propostas or []:
        if not isinstance(proposta, dict):
            continue
        numero = str(proposta.get("numero_proposta") or "").strip()
        if numero:
            indice[numero] = proposta
    return indice


def _linha_com_transicao(antes: dict[str, Any], depois: dict[str, Any]) -> dict[str, Any]:
    linha = dict(depois)
    linha["status_anterior"] = str(antes.get("status") or "—")
    linha["status_atual"] = str(depois.get("status") or "—")
    return linha


def comparar_fechamento(
    snapshot: dict[str, Any] | None,
    propostas_atuais: Iterable[dict[str, Any]] | None,
    hoje: date | None = None,
) -> dict[str, Any]:
    """Compara a fotografia da manhã com a situação atual do banco.

    Categorias:
    - entregues: estavam abertas de manhã e agora estão Entregues;
    - encerradas: saíram da operação por cancelamento/arquivamento válido;
    - avancaram: continuam abertas, mas o status resumido mudou;
    - novas: passaram a integrar a agenda depois do registro da manhã;
    - sem_alteracao: continuam abertas com o mesmo status;
    - pendentes: fotografia atual completa para o próximo período.
    """
    hoje = hoje or date.today()
    snapshot = snapshot or {}
    manha = [x for x in snapshot.get("linhas", []) if isinstance(x, dict)] if snapshot_valido(snapshot) else []
    atual = montar_agenda_anna(propostas_atuais, hoje)

    manha_por_numero = {
        str(x.get("numero_proposta") or "").strip(): x
        for x in manha
        if str(x.get("numero_proposta") or "").strip()
    }
    atual_por_numero = {
        str(x.get("numero_proposta") or "").strip(): x
        for x in atual
        if str(x.get("numero_proposta") or "").strip()
    }
    propostas_por_numero = _indice_propostas(propostas_atuais)

    entregues: list[dict[str, Any]] = []
    encerradas: list[dict[str, Any]] = []
    avancaram: list[dict[str, Any]] = []
    sem_alteracao: list[dict[str, Any]] = []

    for numero, antes in manha_por_numero.items():
        depois = atual_por_numero.get(numero)
        if depois is not None:
            if str(antes.get("status") or "") != str(depois.get("status") or ""):
                avancaram.append(_linha_com_transicao(antes, depois))
            else:
                sem_alteracao.append(dict(depois))
            continue

        proposta = propostas_por_numero.get(numero, {})
        estado = resumo_status(proposta)
        linha_saida = dict(antes)
        if estado.get("entregue"):
            linha_saida["status_atual"] = "Entregue"
            entregues.append(linha_saida)
        elif proposta_encerrada(proposta):
            linha_saida["status_atual"] = "Encerrado / cancelado"
            encerradas.append(linha_saida)
        else:
            # Situação defensiva: se o registro desapareceu da agenda sem marco
            # oficial reconhecível, não o contamos como concluído.
            linha_saida["status_atual"] = "Saiu da agenda — conferir"
            encerradas.append(linha_saida)

    novas = [
        dict(linha)
        for numero, linha in atual_por_numero.items()
        if numero not in manha_por_numero
    ]

    return {
        "registrado_em": snapshot.get("registrado_em") if snapshot_valido(snapshot) else "",
        "abertos_manha": len(manha_por_numero),
        "entregues": entregues,
        "encerradas": encerradas,
        "avancaram": avancaram,
        "novas": novas,
        "sem_alteracao": sem_alteracao,
        "pendentes": atual,
        "resumo": {
            "abertos_manha": len(manha_por_numero),
            "entregues": len(entregues),
            "encerradas": len(encerradas),
            "avancaram": len(avancaram),
            "novas": len(novas),
            "seguem_abertos": len(atual),
            "sem_alteracao": len(sem_alteracao),
        },
    }


def _fmt_registro(valor: Any) -> str:
    texto = str(valor or "").strip()
    if not texto:
        return "—"
    try:
        return datetime.fromisoformat(texto).strftime("%d/%m/%Y às %H:%M")
    except (TypeError, ValueError):
        return texto


def gerar_pdf_fechamento(
    comparativo: dict[str, Any] | None,
    gerado_em: datetime | None = None,
) -> bytes | None:
    """Gera relatório A4 paisagem do fechamento, exclusivamente com dados."""
    try:
        import io
        import html as html_lib
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    except Exception:
        return None

    comparativo = comparativo or {}
    resumo = comparativo.get("resumo") if isinstance(comparativo.get("resumo"), dict) else {}
    gerado_em = gerado_em or datetime.now()
    saida = io.BytesIO()
    pagina = (A4[1], A4[0])
    doc = SimpleDocTemplate(
        saida,
        pagesize=pagina,
        rightMargin=8 * mm,
        leftMargin=8 * mm,
        topMargin=9 * mm,
        bottomMargin=11 * mm,
        title="Fechamento Diário da Anna",
        author="AlphaFest Manager",
    )
    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle("AnnaFechTituloHF19", parent=estilos["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=17, spaceAfter=2 * mm)
    h2 = ParagraphStyle("AnnaFechH2HF19", parent=estilos["Heading2"], fontName="Helvetica-Bold", fontSize=10, leading=12, spaceBefore=2 * mm, spaceAfter=1.5 * mm)
    normal = ParagraphStyle("AnnaFechNormalHF19", parent=estilos["Normal"], fontName="Helvetica", fontSize=8, leading=9.5, spaceAfter=2 * mm)
    celula = ParagraphStyle("AnnaFechCelulaHF19", parent=normal, fontSize=7.1, leading=8.3, spaceAfter=0)
    celula_bold = ParagraphStyle("AnnaFechCelulaBoldHF19", parent=celula, fontName="Helvetica-Bold")
    cab = ParagraphStyle("AnnaFechCabHF19", parent=celula_bold, textColor=colors.white, fontSize=6.9, leading=8)

    elementos = [
        Paragraph("ALPHAFEST ITATIBA — Fechamento Diário da Anna", titulo),
        Paragraph(
            f"Início registrado em <b>{html_lib.escape(_fmt_registro(comparativo.get('registrado_em')))}</b> · "
            f"Fechamento emitido em <b>{gerado_em.strftime('%d/%m/%Y às %H:%M')}</b><br/>"
            f"Abertos pela manhã: {int(resumo.get('abertos_manha', 0) or 0)} · "
            f"Entregues: {int(resumo.get('entregues', 0) or 0)} · "
            f"Avançaram: {int(resumo.get('avancaram', 0) or 0)} · "
            f"Novos: {int(resumo.get('novas', 0) or 0)} · "
            f"Seguem abertos: {int(resumo.get('seguem_abertos', 0) or 0)}",
            normal,
        ),
    ]

    def tabela_secao(titulo_secao: str, linhas: list[dict[str, Any]], tipo: str = "normal") -> None:
        elementos.append(Paragraph(titulo_secao, h2))
        if not linhas:
            elementos.append(Paragraph("Nenhum registro nesta seção.", normal))
            return
        if tipo == "transicao":
            dados = [[Paragraph(x, cab) for x in ("PROPOSTA", "CLIENTE", "STATUS DA MANHÃ", "STATUS ATUAL", "ENTREGA")]]
            for x in linhas:
                dados.append([
                    Paragraph(html_lib.escape(str(x.get("numero_proposta") or "—")), celula_bold),
                    Paragraph(html_lib.escape(str(x.get("cliente_nome") or "Cliente")), celula_bold),
                    Paragraph(html_lib.escape(str(x.get("status_anterior") or "—")), celula),
                    Paragraph(html_lib.escape(str(x.get("status_atual") or x.get("status") or "—")), celula),
                    Paragraph(html_lib.escape(str(x.get("data_entrega") or "—")), celula_bold),
                ])
            widths = [39 * mm, 49 * mm, 70 * mm, 70 * mm, 29 * mm]
        else:
            dados = [[Paragraph(x, cab) for x in ("PROPOSTA", "STATUS", "CLIENTE", "WHATSAPP", "PRODUTO(S)", "ENTREGA")]]
            for x in linhas:
                dados.append([
                    Paragraph(html_lib.escape(str(x.get("numero_proposta") or "—")), celula_bold),
                    Paragraph(html_lib.escape(str(x.get("status_atual") or x.get("status") or "—")), celula),
                    Paragraph(html_lib.escape(str(x.get("cliente_nome") or "Cliente")), celula_bold),
                    Paragraph(html_lib.escape(str(x.get("telefone") or "—")), celula),
                    Paragraph(html_lib.escape(str(x.get("produtos") or "—")), celula),
                    Paragraph(html_lib.escape(str(x.get("data_entrega") or "—")), celula_bold),
                ])
            widths = [35 * mm, 51 * mm, 39 * mm, 31 * mm, 92 * mm, 29 * mm]
        tabela = Table(dados, repeatRows=1, colWidths=widths, hAlign="LEFT")
        estilos_t = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#30343b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#8c8c8c")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
        for i in range(1, len(dados)):
            if i % 2 == 0:
                estilos_t.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f2f2f2")))
        tabela.setStyle(TableStyle(estilos_t))
        elementos.extend([tabela, Spacer(1, 2 * mm)])

    tabela_secao("1. Entregues / concluídos desde o início do dia", list(comparativo.get("entregues") or []))
    tabela_secao("2. Pedidos que avançaram de status", list(comparativo.get("avancaram") or []), "transicao")
    tabela_secao("3. Novos pedidos/propostas que entraram depois da abertura", list(comparativo.get("novas") or []))
    if comparativo.get("encerradas"):
        tabela_secao("4. Encerrados/cancelados durante o dia", list(comparativo.get("encerradas") or []))
        pend_titulo = "5. Pendentes para o próximo período"
    else:
        pend_titulo = "4. Pendentes para o próximo período"
    tabela_secao(pend_titulo, list(comparativo.get("pendentes") or []))

    elementos.append(Paragraph(
        "Relatório comparativo somente leitura. Nenhum status é alterado ao registrar a abertura ou ao gerar este fechamento.",
        normal,
    ))

    def _rodape(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.drawString(8 * mm, 5 * mm, "AlphaFest Manager · Fechamento Diário da Anna")
        canvas.drawRightString(pagina[0] - 8 * mm, 5 * mm, f"Página {_doc.page}")
        canvas.restoreState()

    doc.build(elementos, onFirstPage=_rodape, onLaterPages=_rodape)
    return saida.getvalue()
