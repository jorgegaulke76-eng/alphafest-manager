from datetime import date, datetime

from anna_agenda_service import montar_agenda_anna
from anna_fechamento_service import (
    criar_snapshot_inicio,
    comparar_fechamento,
    gerar_pdf_fechamento,
    snapshot_valido,
)


def _prop(numero, entrega, *, aprovado=False, pago=False, pronto=False, entregue=False, encerrado=False, status_comercial="", cliente="Cliente"):
    return {
        "numero_proposta": numero,
        "data_entrega": entrega,
        "cliente_nome": cliente,
        "whatsapp": "11999999999",
        "aprovado": aprovado,
        "pago": pago,
        "pronto": pronto,
        "entregue": entregue,
        "encerrado": encerrado,
        "status_comercial": status_comercial,
        "itens": [{"produto": "Caneca", "quantidade": 2}],
    }


def test_snapshot_inicio_e_compacto_serializavel():
    linhas = montar_agenda_anna([_prop("P1", "03/09/2026")], date(2026, 9, 2))
    snapshot = criar_snapshot_inicio(linhas, datetime(2026, 9, 2, 8, 5))
    assert snapshot_valido(snapshot)
    assert snapshot["registrado_em"] == "2026-09-02T08:05:00"
    assert len(snapshot["linhas"]) == 1
    assert "data_entrega_obj" not in snapshot["linhas"][0]


def test_fechamento_identifica_entregue_desde_a_manha():
    manha = montar_agenda_anna([_prop("P1", "02/09/2026", aprovado=True, pago=True, pronto=True)], date(2026, 9, 2))
    snapshot = criar_snapshot_inicio(manha, datetime(2026, 9, 2, 8, 0))
    atual = [_prop("P1", "02/09/2026", aprovado=True, pago=True, pronto=True, entregue=True)]
    comp = comparar_fechamento(snapshot, atual, date(2026, 9, 2))
    assert comp["resumo"]["entregues"] == 1
    assert comp["resumo"]["seguem_abertos"] == 0
    assert comp["entregues"][0]["status_atual"] == "Entregue"


def test_fechamento_identifica_avanco_sem_duplicar_pendente():
    manha = montar_agenda_anna([_prop("P1", "05/09/2026", aprovado=False)], date(2026, 9, 2))
    snapshot = criar_snapshot_inicio(manha, datetime(2026, 9, 2, 8, 0))
    atual = [_prop("P1", "05/09/2026", aprovado=True, pago=True)]
    comp = comparar_fechamento(snapshot, atual, date(2026, 9, 2))
    assert comp["resumo"]["avancaram"] == 1
    assert comp["resumo"]["seguem_abertos"] == 1
    assert comp["avancaram"][0]["status_anterior"] == "Aguardando aprovação"
    assert comp["avancaram"][0]["status_atual"] == "Aprovado · Pago"


def test_fechamento_identifica_novos_pedidos_apos_abertura():
    snapshot = criar_snapshot_inicio([], datetime(2026, 9, 2, 8, 0))
    atual = [_prop("NOVO", "10/09/2026")]
    comp = comparar_fechamento(snapshot, atual, date(2026, 9, 2))
    assert comp["resumo"]["novas"] == 1
    assert comp["novas"][0]["numero_proposta"] == "NOVO"


def test_fechamento_separa_cancelamento_de_entrega():
    manha = montar_agenda_anna([_prop("P1", "05/09/2026")], date(2026, 9, 2))
    snapshot = criar_snapshot_inicio(manha, datetime(2026, 9, 2, 8, 0))
    atual = [_prop("P1", "05/09/2026", encerrado=True, status_comercial="cancelado")]
    comp = comparar_fechamento(snapshot, atual, date(2026, 9, 2))
    assert comp["resumo"]["encerradas"] == 1
    assert comp["resumo"]["entregues"] == 0


def test_fechamento_mantem_sem_alteracao_e_pendente():
    atual = [_prop("P1", "05/09/2026", aprovado=True, pago=True)]
    manha = montar_agenda_anna(atual, date(2026, 9, 2))
    snapshot = criar_snapshot_inicio(manha, datetime(2026, 9, 2, 8, 0))
    comp = comparar_fechamento(snapshot, atual, date(2026, 9, 2))
    assert comp["resumo"]["sem_alteracao"] == 1
    assert comp["resumo"]["seguem_abertos"] == 1
    assert comp["sem_alteracao"][0]["numero_proposta"] == "P1"


def test_pdf_fechamento_e_textual_sem_imagens():
    manha_props = [
        _prop("P1", "02/09/2026", aprovado=True, pago=True, pronto=True, cliente="Entregue"),
        _prop("P2", "05/09/2026", aprovado=False, cliente="Avançou"),
    ]
    manha = montar_agenda_anna(manha_props, date(2026, 9, 2))
    snapshot = criar_snapshot_inicio(manha, datetime(2026, 9, 2, 8, 0))
    atual = [
        _prop("P1", "02/09/2026", aprovado=True, pago=True, pronto=True, entregue=True, cliente="Entregue"),
        _prop("P2", "05/09/2026", aprovado=True, pago=True, cliente="Avançou"),
        _prop("P3", "10/09/2026", cliente="Novo"),
    ]
    comp = comparar_fechamento(snapshot, atual, date(2026, 9, 2))
    pdf = gerar_pdf_fechamento(comp, datetime(2026, 9, 2, 18, 0))
    assert pdf and pdf.startswith(b"%PDF")
    assert b"/Subtype /Image" not in pdf
