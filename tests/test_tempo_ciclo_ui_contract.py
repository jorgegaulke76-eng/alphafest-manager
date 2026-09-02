from pathlib import Path


def test_hf27_ui_expoe_memoria_sem_promessa_capacidade():
    src = Path("app.py").read_text(encoding="utf-8")
    assert "⏱️ Memória de tempos de produção · HF27" in src
    assert "Ciclos observados" in src
    assert "Sem início confiável" in src
    assert "Ainda NÃO é usado como capacidade exata" in src
    assert "Mediana do ciclo" in src


def test_hf27_importacao_e_resumo_sao_resilientes():
    src = Path("app.py").read_text(encoding="utf-8")
    assert "TEMPO_CICLO_IMPORT_ERROR" in src
    assert "_tempo_ciclo_resumir(tarefas_central" in src
