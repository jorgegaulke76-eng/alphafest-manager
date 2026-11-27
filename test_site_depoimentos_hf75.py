"""HF75: cards de depoimentos em linhas e colunas responsivas."""
import re
import unittest
from site_home_content_service import HOME_CONTENT_CSS, testimonials_html


class TestDepoimentosGradeHF75(unittest.TestCase):
    def test_grade_desktop_tablet_mobile_sem_rolagem_lateral(self):
        css = HOME_CONTENT_CSS
        regras = re.findall(r"\.hf6514-testimonials-track\{([^}]*)\}", css)
        self.assertEqual(len(regras), 3)
        self.assertIn("grid-template-columns:repeat(3,minmax(0,1fr))", regras[0])
        self.assertIn("grid-template-columns:repeat(2,minmax(0,1fr))", regras[1])
        self.assertIn("grid-template-columns:minmax(0,1fr)", regras[2])
        for regra in regras:
            for proibido in ("overflow-x:auto", "grid-auto-flow:column",
                             "grid-auto-columns", "scroll-snap-type"):
                self.assertNotIn(proibido, regra)

    def test_acrescentar_cards_mantem_estrutura_e_ordem(self):
        imagens = [
            {"kind": "image", "active": True, "name": f"Cliente {i}",
             "image_src": f"https://exemplo.invalid/{i}.png"}
            for i in range(1, 9)
        ]
        html = testimonials_html({"testimonials": imagens})
        self.assertEqual(html.count('class="hf6514-testimonial hf6514-testimonial-image"'), 8)
        self.assertEqual(html.count('class="hf6514-testimonials-track"'), 1)
        posicoes = [html.index(f"https://exemplo.invalid/{i}.png") for i in range(1, 9)]
        self.assertEqual(posicoes, sorted(posicoes))
        self.assertEqual(html.count('class="hf6514-testimonial-dialog"'), 1)

    def test_nao_repete_mensagem_ou_altera_texto(self):
        html = testimonials_html({"testimonials": [
            {"kind": "image", "image_src": "https://exemplo.invalid/1.png",
             "text": "Mensagem escrita dentro da imagem"},
            {"kind": "text", "name": "Cliente", "text": "Muito obrigado!"}
        ]})
        self.assertEqual(html.count("O carinho dos nossos clientes"), 1)
        self.assertNotIn("Mensagem escrita dentro da imagem", html)
        self.assertIn("Muito obrigado!", html)


if __name__ == "__main__":
    unittest.main()
