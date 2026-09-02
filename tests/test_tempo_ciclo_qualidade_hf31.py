from tempo_ciclo_producao_service import resumir_tempos_observados


def _tarefa(idx, minutos, qtd=1):
    return {
        "id": f"P{idx}::0",
        "numero_proposta": f"P{idx}",
        "cliente_nome": f"Cliente {idx}",
        "produto": "PAPEL DE ARROZ",
        "quantidade": qtd,
        "status": "Pronto",
        "ciclos_observados": [{
            "iniciado_em": f"01/09/2026 0{idx}:00" if idx < 10 else "01/09/2026 10:00",
            "concluido_em": f"01/09/2026 0{idx}:30" if idx < 10 else "02/09/2026 06:47",
            "duracao_minutos": minutos,
            "origem": "teste_hf31",
        }],
    }


def test_hf31_sinaliza_amostra_extrema_sem_excluir_da_base():
    tarefas = [
        _tarefa(1, 30, 1),
        _tarefa(2, 32, 1),
        _tarefa(3, 37, 2),
        _tarefa(4, 1247, 1),
    ]
    r = resumir_tempos_observados(tarefas)
    assert r["total_amostras"] == 4
    assert r["total_amostras_para_revisar"] == 1
    linha = r["produtos"][0]
    assert linha["amostras"] == 4
    assert linha["mediana"] == "34 min"
    assert linha["minimo"] == "30 min"
    assert linha["maximo"] == "20h 47min"
    assert linha["faixa_central_minimo"] == "30 min"
    assert linha["faixa_central_maximo"] == "37 min"
    assert linha["amostras_atipicas"] == 1
    assert "Revisar 1" in linha["qualidade"]
    assert linha["lotes_observados"] == "1 un × 3 · 2 un × 1"
    rev = r["amostras_para_revisar"][0]
    assert rev["numero_proposta"] == "P4"
    assert rev["cliente_nome"] == "Cliente 4"
    assert rev["duracao_minutos"] == 1247
    assert "sem exclusão automática" in rev["motivo_revisao"]


def test_hf31_nao_cria_alerta_com_variacao_normal():
    tarefas = [_tarefa(1, 30), _tarefa(2, 32), _tarefa(3, 35), _tarefa(4, 37)]
    r = resumir_tempos_observados(tarefas)
    assert r["total_amostras"] == 4
    assert r["total_amostras_para_revisar"] == 0
    linha = r["produtos"][0]
    assert linha["faixa_central_minimo"] == "30 min"
    assert linha["faixa_central_maximo"] == "37 min"
    assert linha["amostras_atipicas"] == 0
    assert linha["qualidade"] == "Base em formação"
