from datetime import date

from anna_agenda_service import montar_agenda_anna, resumo_agenda_anna, status_resumido_agenda


def _prop(numero, entrega, *, aprovado=False, pago=False, pronto=False, entregue=False, encerrado=False, cliente="Cliente", telefone="11999999999", itens=None, mensal=False):
    return {
        "numero_proposta": numero,
        "data_entrega": entrega,
        "cliente_nome": cliente,
        "whatsapp": telefone,
        "aprovado": aprovado,
        "pago": pago,
        "pronto": pronto,
        "entregue": entregue,
        "encerrado": encerrado,
        "faturamento_mensal": mensal,
        "itens": itens or [{"produto": "Caneca", "quantidade": 2}],
    }


def test_agenda_traz_todas_as_abertas_e_exclui_concluidas_encerradas():
    hoje = date(2026, 9, 2)
    propostas = [
        _prop("P1", "03/09/2026", aprovado=False),
        _prop("P2", "02/09/2026", aprovado=True, pago=True),
        _prop("P3", "01/09/2026", aprovado=True, pago=True, entregue=True),
        _prop("P4", "05/09/2026", encerrado=True),
    ]
    linhas = montar_agenda_anna(propostas, hoje)
    assert [x["numero_proposta"] for x in linhas] == ["P2", "P1"]


def test_agenda_contem_somente_campos_operacionais_solicitados():
    hoje = date(2026, 9, 2)
    linha = montar_agenda_anna([
        _prop(
            "PROP-123",
            "05/09/2026",
            cliente="Ana Teste",
            telefone="11988887777",
            itens=[
                {"produto": "Chaveiro", "quantidade": 10},
                {"produto": "Tag", "quantidade": 20},
            ],
        )
    ], hoje)[0]
    assert linha["numero_proposta"] == "PROP-123"
    assert linha["cliente_nome"] == "Ana Teste"
    assert linha["telefone"] == "11988887777"
    assert "10× Chaveiro" in linha["produtos"]
    assert "20× Tag" in linha["produtos"]
    assert linha["data_entrega"] == "05/09/2026"
    assert "imagem" not in linha
    assert "foto" not in linha
    assert "video" not in linha


def test_status_resumido_distingue_marcos_reais_sem_inferir_producao():
    hoje = date(2026, 9, 2)
    assert status_resumido_agenda(_prop("P1", "04/09/2026"), hoje) == "Aguardando aprovação"
    assert status_resumido_agenda(_prop("P2", "04/09/2026", aprovado=True), hoje) == "Aprovado · Pagamento pendente"
    assert status_resumido_agenda(_prop("P3", "04/09/2026", aprovado=True, pago=True), hoje) == "Aprovado · Pago"
    assert status_resumido_agenda(_prop("P4", "04/09/2026", aprovado=True, pago=True, pronto=True), hoje) == "Pronto / aguardando retirada ou entrega · Pago"
    assert status_resumido_agenda(_prop("P5", "04/09/2026", aprovado=True, mensal=True), hoje) == "Aprovado · Mensal"


def test_agenda_marca_prazo_vencido_e_entrega_hoje_e_ordena_urgencia():
    hoje = date(2026, 9, 2)
    linhas = montar_agenda_anna([
        _prop("FUTURO", "10/09/2026"),
        _prop("SEM-DATA", ""),
        _prop("HOJE", "02/09/2026", aprovado=True, pago=True),
        _prop("ATRASO", "01/09/2026", aprovado=True, pago=True),
    ], hoje)
    assert [x["numero_proposta"] for x in linhas] == ["ATRASO", "HOJE", "FUTURO", "SEM-DATA"]
    assert linhas[0]["status"].startswith("ATRASADO")
    assert linhas[1]["status"].startswith("Entrega hoje")


def test_resumo_agenda_conta_estagios():
    hoje = date(2026, 9, 2)
    linhas = montar_agenda_anna([
        _prop("A", "03/09/2026"),
        _prop("B", "01/09/2026", aprovado=True, pago=True),
        _prop("C", "04/09/2026", aprovado=True, pago=True, pronto=True),
    ], hoje)
    resumo = resumo_agenda_anna(linhas)
    assert resumo == {
        "abertas": 3,
        "aguardando_aprovacao": 1,
        "em_producao": 1,
        "prontas": 1,
        "atrasadas": 1,
    }


def test_pdf_agenda_e_imprimivel_e_nao_embute_imagens():
    from datetime import datetime
    from anna_agenda_service import gerar_pdf_agenda_anna

    linhas = montar_agenda_anna([
        _prop("P1", "02/09/2026", aprovado=True, pago=True, cliente="Cliente PDF")
    ], date(2026, 9, 2))
    pdf = gerar_pdf_agenda_anna(linhas, "Início do dia", datetime(2026, 9, 2, 8, 0))
    assert pdf and pdf.startswith(b"%PDF")
    # O gerador usa exclusivamente texto e tabela; nenhum XObject de imagem deve existir.
    assert b"/Subtype /Image" not in pdf


def test_agenda_recupera_pedido_pago_com_marca_comercial_antiga():
    hoje = date(2026, 9, 2)
    proposta = _prop("P-RECUPERA", "30/09/2026", aprovado=True, pago=True)
    proposta.update({
        "nao_fechado_sem_retorno": True,
        "encerrado": True,
        "status_comercial": "nao_fechado_sem_retorno",
    })
    linhas = montar_agenda_anna([proposta], hoje)
    assert len(linhas) == 1
    assert linhas[0]["numero_proposta"] == "P-RECUPERA"
    assert linhas[0]["status"] == "Aprovado · Pago"


def test_agenda_mantem_cancelamento_explicito_fora_mesmo_se_pago():
    hoje = date(2026, 9, 2)
    proposta = _prop("P-CANCELA", "30/09/2026", aprovado=True, pago=True)
    proposta.update({"status_comercial": "cancelado", "encerrado": True})
    assert montar_agenda_anna([proposta], hoje) == []


def test_status_atraso_separa_producao_saida_e_prazo_sem_aprovacao():
    hoje = date(2026, 9, 2)
    assert status_resumido_agenda(_prop("P-A", "01/09/2026", aprovado=True, pago=True), hoje).startswith("ATRASADO · Aprovado · Pago")
    assert status_resumido_agenda(_prop("P-B", "01/09/2026", aprovado=True, pago=True, pronto=True), hoje).startswith("SAÍDA ATRASADA · Pronto")
    assert status_resumido_agenda(_prop("P-C", "01/09/2026", aprovado=False), hoje).startswith("Prazo vencido · Aguardando aprovação")
