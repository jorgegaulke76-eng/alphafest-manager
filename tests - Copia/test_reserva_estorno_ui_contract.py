from pathlib import Path


def _src():
    return (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")


def test_hf28_expoe_reservas_ativas_para_estorno_separado_da_fila_de_liberacao():
    src = _src()
    assert "↩️ Reservas/consumos ativos — corrigir ou estornar" in src
    assert "Pedido com reserva/consumo ativo" in src
    assert "i8124_consumo_ativo_estorno" in src
    # A fonte da seleção deve ser a lista de controles já ativos, não a fila que exclui reservados.
    assert "ativos_estorno_i8124" in src
    assert "for resumo, consumo in resumos_i8124" in src


def test_hf28_estorno_ativo_reutiliza_fluxo_auditado_do_pedido():
    src = _src()
    assert "↩️ Estornar liberação de materiais" in src
    assert "_i8124_estornar_consumo(" in src
    assert "Confirmo o estorno auditado deste pedido" in src
    assert "Este pedido possui somente reserva ativa. O estorno libera a reserva sem alterar o saldo físico" in src
    assert "Este pedido já possui consumo físico registrado" in src


def test_hf28_nao_orienta_estorno_generico_para_reserva_de_pedido():
    src = _src()
    # O fluxo próprio já preserva a regra homologada: reserva sem consumo não cria devolução física;
    # consumo real usa estorno auditado vinculado ao pedido.
    assert 'registrar_auditoria("Estornar reserva/consumo do pedido"' in src
    assert '"Estorno de consumo do pedido"' in src
