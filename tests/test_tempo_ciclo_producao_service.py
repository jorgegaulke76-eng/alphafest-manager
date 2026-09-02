from tempo_ciclo_producao_service import (
    aplicar_transicao_ciclo,
    amostras_timeline_legado,
    extrair_amostras,
    formatar_duracao,
    resumir_tempos_observados,
)


def test_iniciar_e_concluir_ciclo_observado():
    t = {"id": "P1::0", "produto": "Topo", "status": "Pronto para produzir", "timeline": []}
    t = aplicar_transicao_ciclo(t, "Pronto para produzir", "Em produção", now_text="02/09/2026 10:00", usuario_nome="Jorge")
    assert t["ciclo_observado_atual"]["iniciado_em"] == "02/09/2026 10:00"
    t["status"] = "Em produção"
    t = aplicar_transicao_ciclo(t, "Em produção", "Pronto", now_text="02/09/2026 12:30", usuario_nome="Jorge")
    assert "ciclo_observado_atual" not in t
    assert t["ciclos_observados"][-1]["duracao_minutos"] == 150
    assert t["ultimo_ciclo_observado_minutos"] == 150


def test_nao_inventa_ciclo_ao_pular_direto_para_pronto():
    t = {"id": "P1::0", "produto": "Topo", "status": "Arte pendente"}
    r = aplicar_transicao_ciclo(t, "Arte pendente", "Pronto", now_text="02/09/2026 12:30", usuario_nome="Jorge")
    assert not r.get("ciclos_observados")
    assert "ciclo_observado_atual" not in r


def test_interrupcao_remove_inicio_sem_criar_amostra():
    t = {"ciclo_observado_atual": {"iniciado_em": "02/09/2026 10:00"}}
    r = aplicar_transicao_ciclo(t, "Em produção", "Arte pendente", now_text="02/09/2026 11:00")
    assert "ciclo_observado_atual" not in r
    assert not r.get("ciclos_observados")
    assert r["ciclo_observado_interrompido_em"] == "02/09/2026 11:00"


def test_timeline_legada_recupera_somente_par_explicito():
    t = {
        "timeline": [
            {"data": "01/09/2026 08:00", "descricao": "Central de Produção: Pronto para produzir → Em produção por Jorge"},
            {"data": "01/09/2026 10:15", "descricao": "Central de Produção: Em produção → Pronto por Jorge"},
        ]
    }
    a = amostras_timeline_legado(t)
    assert len(a) == 1
    assert a[0]["duracao_minutos"] == 135
    assert a[0]["origem"] == "timeline_fluxo_recuperada"


def test_extracao_nao_duplica_amostra_persistida_e_timeline():
    t = {
        "id": "P1::0", "numero_proposta": "P1", "produto": "Caneca", "processos": ["Montagem"],
        "ciclos_observados": [{
            "iniciado_em": "01/09/2026 08:00", "concluido_em": "01/09/2026 10:00",
            "duracao_minutos": 120, "origem": "hf27_transicao_confirmada",
        }],
        "timeline": [
            {"data": "01/09/2026 08:00", "descricao": "Pronto para produzir → Em produção"},
            {"data": "01/09/2026 10:00", "descricao": "Em produção → Pronto"},
        ],
    }
    a = extrair_amostras([t])
    assert len(a) == 1
    assert a[0]["produto"] == "Caneca"


def test_resumo_separa_em_producao_sem_inicio_confiavel():
    tarefas = [
        {"id": "A", "produto": "Tag", "status": "Em produção"},
        {"id": "B", "produto": "Tag", "status": "Em produção", "ciclo_observado_atual": {"iniciado_em": "02/09/2026 14:00"}},
        {"id": "C", "produto": "Tag", "status": "Pronto", "ciclos_observados": [
            {"iniciado_em": "01/09/2026 10:00", "concluido_em": "01/09/2026 11:30", "duracao_minutos": 90},
        ]},
    ]
    r = resumir_tempos_observados(tarefas)
    assert r["total_amostras"] == 1
    assert r["produtos_com_amostras"] == 1
    assert r["em_andamento_com_inicio"] == 1
    assert r["em_producao_sem_inicio_confiavel"] == 1
    assert r["produtos"][0]["mediana"] == "1h 30min"
    assert r["produtos"][0]["nivel"] == "Base inicial"


def test_formatar_duracao():
    assert formatar_duracao(45) == "45 min"
    assert formatar_duracao(120) == "2h"
    assert formatar_duracao(150) == "2h 30min"


def test_fecha_ciclo_existente_usando_inicio_explicito_da_timeline():
    t = {
        "id": "LEG::0", "produto": "Adesivo", "status": "Em produção",
        "timeline": [
            {"data": "02/09/2026 09:00", "descricao": "Status alterado de Pronto para produzir para Em produção"},
        ],
    }
    r = aplicar_transicao_ciclo(t, "Em produção", "Pronto", now_text="02/09/2026 11:00", usuario_nome="Jorge")
    assert r["ciclos_observados"][-1]["duracao_minutos"] == 120
    assert r["ciclos_observados"][-1]["origem"] == "hf27_fechamento_com_inicio_recuperado"


def test_atalho_central_abre_e_fecha_amostra_hf27():
    from producao_operacional_service import planejar_atalho_central
    tarefas = [{"id": "P1::0", "numero_proposta": "P1", "produto": "Topo", "status": "Pronto para produzir", "ativa": True, "timeline": []}]
    inicio = planejar_atalho_central(
        tarefas, numero_proposta="P1", acao="iniciar", pode_iniciar_producao=True,
        pode_marcar_pronto=False, now_text="02/09/2026 08:00", usuario_nome="Jorge",
    )
    assert inicio["tarefas"][0]["ciclo_observado_atual"]["iniciado_em"] == "02/09/2026 08:00"
    fim = planejar_atalho_central(
        inicio["tarefas"], numero_proposta="P1", acao="pronto", pode_iniciar_producao=False,
        pode_marcar_pronto=True, now_text="02/09/2026 09:45", usuario_nome="Jorge",
    )
    assert fim["tarefas"][0]["ciclos_observados"][-1]["duracao_minutos"] == 105


def test_reconciliacao_oficial_pronto_fecha_ciclo_em_producao():
    from fluxo_operacional_service import reconciliar_lista_fluxo
    tarefas = [{
        "id": "P1::0", "numero_proposta": "P1", "produto": "Topo", "status": "Em produção",
        "ativa": True, "timeline": [], "ciclo_observado_atual": {"iniciado_em": "02/09/2026 08:00", "iniciado_por": "Jorge"},
    }]
    props = [{
        "numero_proposta": "P1", "cliente_nome": "Cliente", "aprovado": True, "pronto": True, "entregue": False,
        "itens": [{"produto": "Topo", "quantidade": 1}],
    }]
    novas, alterado = reconciliar_lista_fluxo(tarefas, props, now_text="02/09/2026 10:00")
    assert alterado is True
    assert novas[0]["status"] == "Pronto"
    assert novas[0]["ciclos_observados"][-1]["duracao_minutos"] == 120
