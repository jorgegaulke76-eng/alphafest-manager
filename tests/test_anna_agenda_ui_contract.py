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
    assert '("biblioteca_3d", "🧊 Catálogo 3D")' in fonte
    assert 'acoes["biblioteca_3d"] = list(ACOES_PADRAO)' in fonte
    assert 'O Catálogo 3D é exclusivo do perfil Jorge.' in fonte
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


def test_hf23_catalogo_3d_reaproveita_acervo_e_gera_html_sem_expor_arquivo():
    fonte = Path('app.py').read_text(encoding='utf-8')
    trecho = fonte.split('if pagina_atual == "biblioteca_3d":', 1)[1].split('if pagina_atual == "historico":', 1)[0]
    assert '📤 Gerar Catálogo 3D' in trecho
    assert 'Modelos que entrarão no catálogo' in trecho
    assert '✨ Preparar prévia e catálogo 3D' in trecho
    assert 'gerar_html_catalogo_i87(' in trecho
    assert 'mostrar_precos=False' in trecho
    assert '📥 Gerar Catálogo 3D HTML' in trecho
    assert 'Nenhum arquivo 3D, nome de arquivo ou caminho privado é exposto ao cliente.' in trecho


def test_hf23_catalogo_3d_continua_exclusivo_do_jorge():
    fonte = Path('app.py').read_text(encoding='utf-8')
    bloco_anna = fonte.split('PERMISSOES_PADRAO_ANNA = {', 1)[1].split('}', 1)[0]
    assert 'biblioteca_3d' not in bloco_anna


def test_hf24_agenda_executiva_recebe_o_mesmo_sinal_de_continuidade_do_bloco_detalhado():
    fonte = Path('app.py').read_text(encoding='utf-8')
    trecho = fonte.split('#### 🧠 THU • Agenda executiva', 1)[0].rsplit('retornos_comerciais_hf14 =', 1)[1]
    assert '_sinais_cont_hf21 = (' in trecho
    assert '_thu_comercial_montar_agenda(' in trecho
    assert '_sinais_cont_hf21,' in trecho
    assert 'limite=20' in trecho


def test_hf24_mantem_bloco_sem_avanco_como_auditoria_e_nao_substitui_a_agenda():
    fonte = Path('app.py').read_text(encoding='utf-8')
    assert 'A HF24 também considera o sinal de' in fonte
    assert '#### ⏳ THU • Sem avanço registrado' in fonte
    assert 'fotografia/sinais já calculados acima' in fonte


def test_hf30_arquivos_de_versao_estao_alinhados():
    esperado = '20.4.9-I8.13.5-HF41'
    assert Path('VERSAO').read_text(encoding='utf-8').strip() == esperado
    assert Path('VERSAO.txt').read_text(encoding='utf-8').strip() == esperado


def test_hf25_agenda_executiva_incorpora_radar_preventivo_sem_novo_status():
    fonte = Path("app.py").read_text(encoding="utf-8")
    trecho = fonte.split('#### 🧠 THU • Agenda executiva', 1)[0].rsplit('retornos_comerciais_hf14 =', 1)[1]
    assert '_thu_prevencao_montar_sinais(' in trecho
    assert '_central_prod_agenda_hf25' in trecho
    assert '_sinais_prev_hf25' in trecho
    assert '🛡️ Prevenção dos próximos 10 dias' in fonte
    assert 'não é uma medição exata de capacidade' in fonte
    assert 'prevencao_prazo' in fonte


def test_hf25_atualizacao_parcial_nao_quebra_agenda_executiva():
    fonte = Path('app.py').read_text(encoding='utf-8')
    assert 'inspect.signature(_thu_comercial_montar_agenda)' in fonte
    assert '"sinais_prevencao" in _agenda_params_hf25' in fonte
    assert 'compatibilidade com atualização parcial' in fonte


def test_hf26_plano_de_amanha_fica_dentro_da_agenda_executiva_e_somente_leitura():
    fonte = Path('app.py').read_text(encoding='utf-8')
    assert '🗓️ Plano de amanhã' in fonte
    assert '_thu_plano_amanha_montar(' in fonte
    assert 'não são repetidos aqui' in fonte
    assert 'Nenhuma ação é registrada automaticamente' in fonte


def test_hf26_importacao_do_plano_e_resiliente():
    fonte = Path('app.py').read_text(encoding='utf-8')
    assert 'THU_PLANO_AMANHA_IMPORT_ERROR' in fonte
    assert 'Plano de amanhã indisponível nesta atualização parcial' in fonte
