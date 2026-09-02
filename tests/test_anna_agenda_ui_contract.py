from pathlib import Path


def test_hf20_mantem_pdf_manha_e_oferece_pdf_atualizado_ao_mesmo_tempo():
    fonte = Path('app.py').read_text(encoding='utf-8')
    assert '🖨️ Baixar roteiro registrado — início do dia (PDF)' in fonte
    assert '🔄 Atualizar e baixar agenda atual (PDF)' in fonte
    assert 'anna_agenda_atual_hf20' in fonte
    assert 'agenda_anna_{data_arquivo_hf19}_atual_{hora_arquivo_hf20}.pdf' in fonte


def test_hf20_explica_que_pdf_atual_nao_substitui_snapshot_da_manha():
    fonte = Path('app.py').read_text(encoding='utf-8')
    assert 'O roteiro registrado da manhã permanece congelado para o comparativo.' in fonte
    assert 'sem alterar a fotografia registrada pela manhã' in fonte


def test_hf21_expoe_radar_sem_avanco_somente_leitura_no_jorge():
    fonte = Path('app.py').read_text(encoding='utf-8')
    assert '⏳ THU • Sem avanço registrado' in fonte
    assert 'não houve mudança de status registrada no Manager' in fonte
    assert 'thu_sem_avanco_abrir_hf21_' in fonte


def test_hf21_importacao_do_radar_e_resiliente():
    fonte = Path('app.py').read_text(encoding='utf-8')
    assert 'THU_CONTINUIDADE_IMPORT_ERROR' in fonte
    assert 'O radar de continuidade não foi carregado nesta atualização.' in fonte
