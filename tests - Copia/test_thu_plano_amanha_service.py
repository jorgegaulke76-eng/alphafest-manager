from datetime import date

from thu_plano_amanha_service import montar_plano_amanha, resumo_plano_amanha


def _prop(numero, entrega, *, pronto=False, entregue=False, aprovado=True):
    return {
        "numero_proposta": numero,
        "cliente_nome": f"Cliente {numero}",
        "data_entrega": entrega,
        "aprovado": aprovado,
        "pago": True,
        "pronto": pronto,
        "entregue": entregue,
    }


def _prev(numero, entrega, *, etapa="preparacao", nivel="alta", prioridade=800):
    return {
        "numero_proposta": numero,
        "cliente_nome": f"Cliente {numero}",
        "data_entrega": entrega,
        "dias_para_entrega": 5,
        "situacao_operacional_chave": etapa,
        "nivel": nivel,
        "prioridade": prioridade,
        "motivo": "janela preventiva",
        "acao": "proteger prazo",
    }


def test_reaproveita_sinal_preventivo_como_acao_de_producao():
    plano = montar_plano_amanha([], date(2026, 9, 2), sinais_prevencao=[_prev("P1", "07/09/2026")])
    assert len(plano) == 1
    assert plano[0]["dominio"] == "Produção"
    assert plano[0]["acao"] == "proteger prazo"


def test_material_pendente_vira_bloco_de_materiais():
    plano = montar_plano_amanha([], date(2026, 9, 2), sinais_prevencao=[_prev("P1", "08/09/2026", etapa="aguardando_material")])
    assert plano[0]["dominio"] == "Materiais"
    assert plano[0]["icone"] == "📦"


def test_pronto_com_entrega_amanha_entra_como_saida():
    hoje = date(2026, 9, 2)
    plano = montar_plano_amanha([_prop("P1", "03/09/2026", pronto=True)], hoje)
    assert len(plano) == 1
    assert plano[0]["dominio"] == "Saída"
    assert "amanhã" in plano[0]["motivo"]


def test_nao_pronto_com_entrega_amanha_nao_e_empurrado_para_amanha():
    hoje = date(2026, 9, 2)
    assert montar_plano_amanha([_prop("P1", "03/09/2026", pronto=False)], hoje) == []


def test_atrasado_pronto_nao_entra_no_plano_de_amanha():
    hoje = date(2026, 9, 2)
    assert montar_plano_amanha([_prop("P1", "01/09/2026", pronto=True)], hoje) == []


def test_entregue_nao_entra_mesmo_com_data_amanha():
    hoje = date(2026, 9, 2)
    assert montar_plano_amanha([_prop("P1", "03/09/2026", pronto=True, entregue=True)], hoje) == []


def test_mesmo_pedido_nao_duplica_e_saida_pronta_tem_precedencia():
    hoje = date(2026, 9, 2)
    props = [_prop("P1", "03/09/2026", pronto=True)]
    prev = [_prev("P1", "03/09/2026", etapa="aguardando_material", prioridade=500)]
    plano = montar_plano_amanha(props, hoje, sinais_prevencao=prev)
    assert len(plano) == 1
    assert plano[0]["dominio"] == "Saída"


def test_resumo_separa_dominios():
    plano = [
        {"dominio": "Produção"},
        {"dominio": "Materiais"},
        {"dominio": "Saída"},
        {"dominio": "Produção"},
    ]
    assert resumo_plano_amanha(plano) == {"total": 4, "producao": 2, "materiais": 1, "saidas": 1}
