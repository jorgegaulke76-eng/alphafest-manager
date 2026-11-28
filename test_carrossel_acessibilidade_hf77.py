"""HF77: foco acessivel e alvos de toque no carrossel de destaques."""
import ast
import re
import unittest
from pathlib import Path


class CarrosselHF77(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codigo = Path("site_visual_hf48_service.py").read_text(encoding="utf-8")
        ast.parse(cls.codigo)

    def test_esconde_slides_nao_visiveis_do_foco(self):
        c = self.codigo
        self.assertIn('clone.inert=true;', c)
        self.assertIn('s.inert=!shown;', c)
        self.assertIn('c.inert=true;', c)
        self.assertIn('aria-hidden', c)
        self.assertIn('" inert" if i else ""', c)

    def test_botoes_tem_area_minima_44px(self):
        c = self.codigo
        regras = re.findall(r'\.hf50-carousel-arrow\{([^}]*)\}', c)
        self.assertTrue(any('width:44px' in x and 'height:44px' in x for x in regras))
        dots = re.findall(r'\.hf50-carousel-dot\{([^}]*)\}', c)
        self.assertTrue(any('width:44px' in x and 'height:44px' in x for x in dots))

    def test_mantem_navegacao_e_produtos(self):
        c = self.codigo
        for trecho in (
            'data-hf50-product', 'function forward()', 'function backward()',
            'function jumpTo(n)', "shell.addEventListener('touchstart'",
            'window.addEventListener(\'resize\'',
        ):
            self.assertIn(trecho, c)


if __name__ == "__main__":
    unittest.main()
