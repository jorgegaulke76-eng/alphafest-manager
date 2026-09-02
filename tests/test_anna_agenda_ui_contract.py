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


def test_hf22_biblioteca_3d_existe_somente_para_jorge_na_navegacao():
    fonte = Path('app.py').read_text(encoding='utf-8')
    assert '("biblioteca_3d", "🧊 Biblioteca 3D")' in fonte
    assert 'acoes["biblioteca_3d"] = list(ACOES_PADRAO)' in fonte
    assert 'A Biblioteca 3D é exclusiva do perfil Jorge.' in fonte
    # O conjunto operacional padrão da Anna não recebe a nova aba.
    bloco_anna = fonte.split('PERMISSOES_PADRAO_ANNA = {', 1)[1].split('}', 1)[0]
    assert 'biblioteca_3d' not in bloco_anna


def test_hf22_biblioteca_3d_nao_possui_campo_de_link_externo():
    fonte = Path('app.py').read_text(encoding='utf-8')
    trecho = fonte.split('if pagina_atual == "biblioteca_3d":', 1)[1].split('if pagina_atual == "historico":', 1)[0]
    assert 'Nome *' in trecho
    assert 'Descrição' in trecho
    assert 'Tempo de impressão' in trecho
    assert '1 imagem *' in trecho
    assert 'Arquivo 3D *' in trecho
    assert 'text_input("Link' not in trecho
    assert 'MakerWorld' not in trecho


def test_hf22_so_confirma_cadastro_quando_storage_e_banco_confirmam():
    fonte = Path('app.py').read_text(encoding='utf-8')
    trecho = fonte.split('if pagina_atual == "biblioteca_3d":', 1)[1].split('if pagina_atual == "historico":', 1)[0]
    assert 'upload_private_3d_file' in trecho
    assert 'Nada foi cadastrado para evitar uma falsa sensação de backup.' in trecho
    assert 'save_document("biblioteca_3d_db"' in trecho
    assert 'delete_private_3d_file' in trecho
