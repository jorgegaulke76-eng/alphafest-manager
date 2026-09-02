"""20.4.9-I8.13.5-HF17 — agenda operacional imprimível da Anna.

Camada somente leitura. Consolida propostas/pedidos ainda abertos em linhas
compactas para tela e impressão, sem imagens e sem persistir qualquer dado.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable

from pedido_resumo import resumo_produtos_pedido
from proposal_status import proposta_ativa_operacional, resumo_status


def _data_entrega(valor: Any) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor or "").strip()
    if not texto:
        return None
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(texto[:19] if "T" in texto else texto, formato).date()
        except (TypeError, ValueError):
            continue
    return None


def _telefone(proposta: dict[str, Any]) -> str:
    return str(
        proposta.get("whatsapp")
        or proposta.get("cliente_wa")
        or proposta.get("telefone")
        or proposta.get("cliente_telefone")
        or ""
    ).strip() or "—"


def status_resumido_agenda(proposta: dict[str, Any] | None, hoje: date | None = None) -> str:
    proposta = proposta or {}
    hoje = hoje or date.today()
    estado = resumo_status(proposta)
    entrega = _data_entrega(proposta.get("data_entrega"))

    partes: list[str] = []
    if entrega and entrega < hoje:
        partes.append("ATRASADO")
    elif entrega == hoje:
        partes.append("Entrega hoje")

    if not estado.get("aprovado"):
        partes.append("Aguardando aprovação")
    elif estado.get("pronto"):
        partes.append("Pronto / aguardando saída")
    else:
        partes.append("Em produção")

    if estado.get("aprovado"):
        if estado.get("mensalista"):
            partes.append("Mensal")
        elif estado.get("pago"):
            partes.append("Pago")
        else:
            partes.append("Pagamento pendente")

    return " · ".join(partes)


def montar_agenda_anna(
    propostas: Iterable[dict[str, Any]] | None,
    hoje: date | None = None,
) -> list[dict[str, Any]]:
    """Retorna todas as propostas abertas, ordenadas pela entrega mais urgente."""
    hoje = hoje or date.today()
    linhas: list[dict[str, Any]] = []
    for proposta in propostas or []:
        if not isinstance(proposta, dict) or not proposta_ativa_operacional(proposta):
            continue
        entrega = _data_entrega(proposta.get("data_entrega"))
        linhas.append(
            {
                "numero_proposta": str(proposta.get("numero_proposta") or "—").strip() or "—",
                "status": status_resumido_agenda(proposta, hoje),
                "cliente_nome": str(proposta.get("cliente_nome") or proposta.get("cliente") or "Cliente").strip() or "Cliente",
                "telefone": _telefone(proposta),
                "produtos": resumo_produtos_pedido(proposta, limite=99, max_chars=360),
                "data_entrega": entrega.strftime("%d/%m/%Y") if entrega else "—",
                "data_entrega_obj": entrega,
            }
        )

    def chave(linha: dict[str, Any]):
        entrega = linha.get("data_entrega_obj")
        sem_data = entrega is None
        return (
            1 if sem_data else 0,
            entrega or date.max,
            str(linha.get("cliente_nome") or "").casefold(),
            str(linha.get("numero_proposta") or ""),
        )

    return sorted(linhas, key=chave)


def resumo_agenda_anna(linhas: Iterable[dict[str, Any]] | None) -> dict[str, int]:
    linhas = list(linhas or [])
    return {
        "abertas": len(linhas),
        "aguardando_aprovacao": sum("Aguardando aprovação" in str(x.get("status") or "") for x in linhas),
        "em_producao": sum("Em produção" in str(x.get("status") or "") for x in linhas),
        "prontas": sum("Pronto / aguardando saída" in str(x.get("status") or "") for x in linhas),
        "atrasadas": sum("ATRASADO" in str(x.get("status") or "") for x in linhas),
    }


def gerar_pdf_agenda_anna(
    linhas: Iterable[dict[str, Any]] | None,
    momento: str = "Início do dia",
    gerado_em: datetime | None = None,
) -> bytes | None:
    """Gera PDF A4 paisagem da agenda, sem qualquer imagem ou mídia."""
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

    linhas = list(linhas or [])
    gerado_em = gerado_em or datetime.now()
    saida = io.BytesIO()
    pagina = (A4[1], A4[0])
    doc = SimpleDocTemplate(
        saida,
        pagesize=pagina,
        rightMargin=8 * mm,
        leftMargin=8 * mm,
        topMargin=10 * mm,
        bottomMargin=11 * mm,
        title=f"Agenda Operacional da Anna — {momento}",
        author="AlphaFest Manager",
    )
    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle(
        "AgendaAnnaTituloHF17",
        parent=estilos["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=17,
        spaceAfter=2 * mm,
    )
    subtitulo = ParagraphStyle(
        "AgendaAnnaSubtituloHF17",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=10.5,
        spaceAfter=3 * mm,
    )
    celula = ParagraphStyle(
        "AgendaAnnaCelulaHF17",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=7.4,
        leading=8.8,
    )
    celula_bold = ParagraphStyle(
        "AgendaAnnaCelulaBoldHF17",
        parent=celula,
        fontName="Helvetica-Bold",
    )
    cabecalho = ParagraphStyle(
        "AgendaAnnaCabecalhoHF17",
        parent=celula_bold,
        fontSize=7.2,
        leading=8.4,
        textColor=colors.white,
    )

    resumo = resumo_agenda_anna(linhas)
    elementos = [
        Paragraph("ALPHAFEST ITATIBA — Agenda Operacional da Anna", titulo),
        Paragraph(
            f"<b>{html_lib.escape(str(momento))}</b> · Emitida em {gerado_em.strftime('%d/%m/%Y às %H:%M')} · "
            f"{resumo['abertas']} proposta(s)/pedido(s) aberto(s)<br/>"
            f"Aguardando aprovação: {resumo['aguardando_aprovacao']} · Em produção: {resumo['em_producao']} · "
            f"Prontos: {resumo['prontas']} · Atrasados: {resumo['atrasadas']}",
            subtitulo,
        ),
    ]

    dados = [[
        Paragraph("PROPOSTA", cabecalho),
        Paragraph("STATUS", cabecalho),
        Paragraph("CLIENTE", cabecalho),
        Paragraph("WHATSAPP", cabecalho),
        Paragraph("PRODUTO(S)", cabecalho),
        Paragraph("ENTREGA", cabecalho),
    ]]
    if linhas:
        for linha in linhas:
            dados.append([
                Paragraph(html_lib.escape(str(linha.get("numero_proposta") or "—")), celula_bold),
                Paragraph(html_lib.escape(str(linha.get("status") or "—")), celula),
                Paragraph(html_lib.escape(str(linha.get("cliente_nome") or "Cliente")), celula_bold),
                Paragraph(html_lib.escape(str(linha.get("telefone") or "—")), celula),
                Paragraph(html_lib.escape(str(linha.get("produtos") or "Sem itens informados")), celula),
                Paragraph(html_lib.escape(str(linha.get("data_entrega") or "—")), celula_bold),
            ])
    else:
        dados.append([Paragraph("Nenhuma proposta/pedido aberto neste momento.", celula)] + [""] * 5)

    tabela = Table(
        dados,
        repeatRows=1,
        colWidths=[36 * mm, 44 * mm, 43 * mm, 33 * mm, 96 * mm, 25 * mm],
        hAlign="LEFT",
    )
    estilo_tabela = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#30343b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#8c8c8c")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for i in range(1, len(dados)):
        if i % 2 == 0:
            estilo_tabela.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f2f2f2")))
    if not linhas:
        estilo_tabela.append(("SPAN", (0, 1), (-1, 1)))
    tabela.setStyle(TableStyle(estilo_tabela))
    elementos.extend([tabela, Spacer(1, 3 * mm)])
    elementos.append(Paragraph(
        "Roteiro gerado a partir da situação atual do AlphaFest Manager. Reimprima no fim do dia para conferir o que permaneceu aberto.",
        subtitulo,
    ))

    def _rodape(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.drawString(8 * mm, 5 * mm, f"AlphaFest Manager · {momento}")
        canvas.drawRightString(pagina[0] - 8 * mm, 5 * mm, f"Página {_doc.page}")
        canvas.restoreState()

    doc.build(elementos, onFirstPage=_rodape, onLaterPages=_rodape)
    return saida.getvalue()
