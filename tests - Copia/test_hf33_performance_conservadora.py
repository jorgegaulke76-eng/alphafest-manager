import ast
import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'app.py'


class HF33PerformanceConservadoraTests(unittest.TestCase):
    def test_lazy_module_nao_importa_antes_do_primeiro_uso(self):
        sys.path.insert(0, str(ROOT))
        try:
            lazy_runtime = importlib.import_module('lazy_runtime')
            sys.modules.pop('fractions', None)
            proxy = lazy_runtime.LazyModule('fractions')
            self.assertFalse(proxy.loaded)
            self.assertNotIn('fractions', sys.modules)
            _ = proxy.Fraction
            self.assertTrue(proxy.loaded)
            self.assertIn('fractions', sys.modules)
        finally:
            try:
                sys.path.remove(str(ROOT))
            except ValueError:
                pass

    def test_template_padrao_hf32_foi_preservado(self):
        engine = (ROOT / 'marketing_template_engine.py').read_text(encoding='utf-8')
        app = APP.read_text(encoding='utf-8')
        self.assertIn('DEFAULT_TEMPLATE = "anna_base_dinamica"', engine)
        self.assertIn('MARKETING_DEFAULT_TEMPLATE = "anna_base_dinamica"', app)

    def test_cache_de_documentos_nao_foi_alterado_para_performance(self):
        cfg = (ROOT / 'config.py').read_text(encoding='utf-8')
        app = APP.read_text(encoding='utf-8')
        self.assertIn('DOCUMENT_CACHE_TTL_SECONDS = 30', cfg)
        self.assertIn('cached and (now - cached["time"] < DOCUMENT_CACHE_TTL_SECONDS)', app)
        self.assertIn('invalidate_document_cache', app)

    def test_funcoes_homologadas_recentes_continuam_presentes(self):
        src = APP.read_text(encoding='utf-8')
        contratos = [
            'THU • Agenda executiva',
            'Agenda diária para impressão',
            'Catálogo 3D',
            'Reservas/consumos ativos',
            'Memória de tempos de produção',
            'Central de Oportunidades',
            'Alpha Intelligence',
        ]
        for contrato in contratos:
            self.assertIn(contrato, src, contrato)

    def test_imports_pesados_nao_sao_top_level_obrigatorios(self):
        tree = ast.parse(APP.read_text(encoding='utf-8'))
        top_imports = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                top_imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                top_imports.add(node.module)
        adiados = {
            'altair', 'marketing_template_engine', 'template_library_engine',
            'marketing_prompt_builder', 'marketing_design_intelligence',
            'marketing_ai_engine', 'thu_poses_embedded', 'alpha_intelligence',
            'central_oportunidades', 'openai', 'qrcode',
        }
        self.assertTrue(adiados.isdisjoint(top_imports), sorted(adiados & top_imports))


if __name__ == '__main__':
    unittest.main()
