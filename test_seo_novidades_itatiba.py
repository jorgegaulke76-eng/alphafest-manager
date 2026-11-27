"""Checagens focais das páginas de Novidades, sem redes nem publicação."""
import re
import unittest
from datetime import date
from unittest.mock import patch
from site_posts_service import archive_pages


def post(i, category="Balões"):
    return {
        "id": str(i),
        "title": f"Arte {i}",
        "description": "Personalização sob consulta",
        "category": category,
        "image_data_uri": "data:image/png;base64,AA==",
        "status": "publicado",
        "created_at": "2026-11-27",
    }


class TestSEOArquivoNovidades(unittest.TestCase):
    def test_titulos_descriptions_e_layout_preservados(self):
        lista = [post(i, "Balões" if i < 24 else "Brindes para empresas") for i in range(50)]
        with patch("site_posts_service._commercial_today", return_value=date(2026, 11, 27)):
            paginas = archive_pages(lista, "11972949533")
        self.assertEqual(len(paginas), 3)
        metas = []
        for idx, (path, html) in enumerate(paginas.items(), 1):
            with self.subTest(path=path):
                title = re.search(r'<title>(.*?)</title>', html).group(1)
                desc = re.search(r'<meta name="description" content="([^"]+)"', html).group(1)
                self.assertEqual(html.count('<meta name="description"'), 1)
                self.assertIn("AlphaFest", title)
                self.assertIn("Itatiba", desc)
                self.assertIn(f"página {idx} de 3", desc)
                self.assertIn("Temas desta seleção", html)
                self.assertIn('class="afposts-grid"', html)
                self.assertEqual(html.count('class="afposts-card"'), 24 if idx < 3 else 2)
                self.assertEqual(html.count('class="afposts-cta"'), 24 if idx < 3 else 2)
                self.assertIn('data-afposts-scope', html)
                self.assertIn("rel=\"canonical\"", html)
                metas.append(desc)
        self.assertEqual(len(set(metas)), 3)

    def test_nenhum_rascunho_vaza(self):
        entries = [post(1), {**post(2), "status": "rascunho"}]
        result = archive_pages(entries)
        self.assertNotIn('alt="Arte 2"', result["novidades/index.html"])
        self.assertIn('alt="Arte 1"', result["novidades/index.html"])


if __name__ == "__main__":
    unittest.main()
