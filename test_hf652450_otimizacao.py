"""HF65.24.50: checagens estruturais das proteções de desempenho.

Não importa app.py nem acessa banco, arquivos de clientes ou Streamlit Cloud.
"""
import ast
from pathlib import Path

APP = Path(__file__).with_name('app.py')
TREE = ast.parse(APP.read_text(encoding='utf-8'))


def _guard(call_name, around_line):
    calls = [n for n in ast.walk(TREE)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == call_name and abs(n.lineno - around_line) < 70]
    assert calls, f'{call_name} not found near {around_line}'
    node = calls[0]
    return [ast.unparse(n.test) for n in ast.walk(TREE)
            if isinstance(n, ast.If) and n.lineno < node.lineno <= n.end_lineno]


def test_revisao_catalogo_sob_demanda():
    guards = _guard('carregar_catalogo', 27002)
    assert any('mostrar_catalogo_hf50' in g and 'MODO_SOB_ENCOMENDA_HF38' in g for g in guards)


def test_fila_legada_fora_do_modo_encomenda():
    guards = _guard('_i8124_proposta_na_fila_liberacao', 26963)
    assert any('not MODO_SOB_ENCOMENDA_HF38' in g for g in guards)


def test_restauracao_sob_demanda_e_com_confirmacao():
    source = APP.read_text(encoding='utf-8')
    start = source.index('if st.toggle("🧰 Abrir restauração de backup"')
    end = source.index('    st.divider()', start)
    block = source[start:end]
    assert 'confirmar_restauracao_hf50' in block
    assert 'disabled=not confirmar_restauracao_hf50' in block
    assert 'if salvar_historico_completo(restaurado) is False:' in block
    assert 'key="hf50_mostrar_restauracao", value=False' in block


def test_version_files_synced():
    from json import loads
    root = APP.parent
    a = (root/'VERSAO').read_text().strip()
    b = (root/'VERSAO.txt').read_text().strip()
    c = loads((root/'RELEASE_INFO.json').read_text())['version']
    assert a == b == c
    assert a.endswith('HF65.24.50')
