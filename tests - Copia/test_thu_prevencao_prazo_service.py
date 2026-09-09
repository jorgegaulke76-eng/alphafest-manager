from datetime import date

from thu_prevencao_prazo_service import montar_sinais_prevencao_prazo


def _prop(numero, entrega, *, prazo="10", pronto=False, entregue=False):
    return {
        "numero_proposta": numero,
        "cliente_nome": f"Cliente {numero}",
        "data_entrega": entrega,
        "prazo_dias": prazo,
        "aprovado": True,
        "pago": True,
        "pronto": pronto,
        "entregue": entregue,
    }


def test_detecta_janela_menor_que_prazo_informado_antes_da_urgencia():
    hoje = date(2026, 9, 2)  # quarta
    props = [_prop("P1", "09/09/2026", prazo="10")]
    central = [{"numero_proposta": "P1", "situacao_operacional_chave": "preparacao", "situacao_operacional": "🎨 Preparação / arte"}]
    sinais = montar_sinais_prevencao_prazo(props, hoje, central_producao=central)
    assert len(sinais) == 1
    assert sinais[0]["nivel"] == "alta"
    assert "prazo informado de 10" in sinais[0]["motivo"]


def test_material_pendente_em_prazo_futuro_gera_prevencao():
    hoje = date(2026, 9, 2)
    props = [_prop("P1", "08/09/2026", prazo="2")]
    central = [{"numero_proposta": "P1", "situacao_operacional_chave": "aguardando_material", "situacao_operacional": "🟠 Aguardando material"}]
    sinais = montar_sinais_prevencao_prazo(props, hoje, central_producao=central)
    assert len(sinais) == 1
    assert "material/liberação" in sinais[0]["motivo"]


def test_pedido_em_producao_com_folga_nao_vira_alerta_artificial():
    hoje = date(2026, 9, 2)
    props = [_prop("P1", "10/09/2026", prazo="10")]
    central = [{"numero_proposta": "P1", "situacao_operacional_chave": "em_producao", "situacao_operacional": "🔵 Em produção"}]
    assert montar_sinais_prevencao_prazo(props, hoje, central_producao=central) == []


def test_concentracao_de_tres_pedidos_na_mesma_data_e_sinal_qualitativo():
    hoje = date(2026, 9, 2)
    props = [_prop(f"P{i}", "10/09/2026", prazo="2") for i in range(1, 4)]
    central = [{"numero_proposta": f"P{i}", "situacao_operacional_chave": "pronto_iniciar", "situacao_operacional": "🟢 Pronto para iniciar"} for i in range(1, 4)]
    sinais = montar_sinais_prevencao_prazo(props, hoje, central_producao=central)
    assert len(sinais) == 3
    assert all(x["carga_mesma_data"] == 3 for x in sinais)
    assert all("3 pedidos ainda não Prontos" in x["motivo"] for x in sinais)


def test_entrega_em_ate_dois_dias_fica_para_prioridade_operacional_existente():
    hoje = date(2026, 9, 2)
    props = [_prop("P1", "04/09/2026", prazo="10")]
    central = [{"numero_proposta": "P1", "situacao_operacional_chave": "preparacao"}]
    assert montar_sinais_prevencao_prazo(props, hoje, central_producao=central) == []


def test_pronto_e_entregue_nao_entram_no_radar_preventivo():
    hoje = date(2026, 9, 2)
    props = [
        _prop("P1", "08/09/2026", pronto=True),
        _prop("P2", "08/09/2026", entregue=True),
    ]
    assert montar_sinais_prevencao_prazo(props, hoje) == []
