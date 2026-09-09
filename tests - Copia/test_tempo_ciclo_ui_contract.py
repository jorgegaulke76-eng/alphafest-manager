from pathlib import Path


def test_hf27_ui_expoe_memoria_sem_promessa_capacidade():
    src = Path("app.py").read_text(encoding="utf-8")
    assert "⏱️ Memória de tempos de produção · HF32" in src
    assert "Ciclos observados" in src
    assert "Sem início confiável" in src
    assert "Ainda NÃO é usado como capacidade exata" in src
    assert "Mediana do ciclo" in src


def test_hf27_importacao_e_resumo_sao_resilientes():
    src = Path("app.py").read_text(encoding="utf-8")
    assert "TEMPO_CICLO_IMPORT_ERROR" in src
    assert "_tempo_ciclo_resumir(" in src
    assert "revisoes=_revisoes_ciclo_hf32" in src


def test_hf29_ui_mostra_quais_ciclos_estao_em_andamento_e_abre_pedido():
    src = Path("app.py").read_text(encoding="utf-8")
    assert "Ciclo(s) em andamento — qual pedido está sendo observado" in src
    assert "Início explícito do ciclo" in src
    assert "tempo_ciclo_abrir_hf29_" in src
    assert '"alerta_proposta_numero"' in src


def test_hf30_ui_explica_finalizado_sem_horario_sem_inventar_duracao():
    src = Path("app.py").read_text(encoding="utf-8")
    assert "já finalizado(s)" in src
    assert "não são tratados como em andamento" in src


def test_hf31_ui_expoe_qualidade_da_base_sem_descartar_amostra():
    src = Path("app.py").read_text(encoding="utf-8")
    assert "🔎 Pendentes revisão" in src
    assert "✅ Revisadas" in src
    assert "Faixa central" in src
    assert "Faixa total" in src
    assert "Lotes observados" in src
    assert "Variações detectadas — revisar contexto" in src
    assert "Nenhuma amostra é apagada ou alterada" in src
    assert "tempo_ciclo_revisar_hf32_" in src


def test_hf32_ui_registra_contexto_na_auditoria_sem_excluir_amostra():
    src = Path("app.py").read_text(encoding="utf-8")
    assert "Variações detectadas — revisar contexto" in src
    assert "Contexto da variação" in src
    assert "✅ Registrar revisão" in src
    assert "Revisar tempo de ciclo" in src
    assert "A duração original foi preservada" in src
    assert "revisoes_tempo_ciclo_auditoria" in src
