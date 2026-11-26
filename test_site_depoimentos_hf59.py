"""HF59: depoimentos originais sem legenda repetitiva e com zoom acessível."""
from __future__ import annotations

import html
import unittest
from html.parser import HTMLParser

from site_home_content_service import (
    HOME_CONTENT_CSS, HOME_CONTENT_JS, normalize_home_content_config,
    testimonials_html,
)


class Elementos(HTMLParser):
    def __init__(self):
        super().__init__()
        self.imgs, self.botoes, self.dialogs, self.articles = [], [], [], []
        self.texto = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "img":
            self.imgs.append(a)
        elif tag == "button":
            self.botoes.append(a)
        elif tag == "dialog":
            self.dialogs.append(a)
        elif tag == "article":
            self.articles.append(a)

    def handle_data(self, data):
        self.texto.append(data)


def quatro_imagens():
    return [
        {
            "id": f"original-{i}", "kind": "image", "active": True,
            "name": "Cliente AlphaFest",
            "image_src": f"https://exemplo.invalid/depoimento-{i}.png",
            "text": "Mensagem longa cadastrada que NÃO deve se repetir sob a imagem.",
        }
        for i in range(1, 5)
    ]


class DepoimentosGaleriaHF59(unittest.TestCase):
    def test_quatro_imagens_e_um_unico_texto_apresentacao(self):
        config = {"testimonials": quatro_imagens()}
        rendered = testimonials_html(config)
        p = Elementos()
        p.feed(rendered)
        self.assertEqual(len(p.imgs), 5)  # Quatro artes e a imagem vazia da ampliação.
        self.assertEqual(len(p.articles), 4)
        self.assertEqual(len(p.dialogs), 1)
        self.assertEqual(sum("hf6514-testimonial-zoom" in b.get("class", "") for b in p.botoes), 4)
        self.assertEqual(rendered.count("O carinho dos nossos clientes"), 1)
        self.assertEqual(rendered.count("Cada mensagem que recebemos"), 1)
        self.assertNotIn("Depoimento enviado pela AlphaFest", rendered)
        self.assertNotIn("Mensagem longa cadastrada", rendered)
        self.assertNotIn("★★★★★", rendered)
        self.assertNotIn("<strong>", rendered)
        for i, img in enumerate(p.imgs[:4], 1):
            self.assertEqual(img["src"], f"https://exemplo.invalid/depoimento-{i}.png")
            self.assertIn("Depoimento em imagem", img.get("alt", ""))
        self.assertEqual(len(normalize_home_content_config(config)["testimonials"]), 4)
        self.assertIn("Mensagem longa cadastrada", normalize_home_content_config(config)["testimonials"][0]["text"])

    def test_fonte_data_base64_uma_vez_sem_duplicar_imagem(self):
        base64_src = "data:image/png;base64,AAABBCDD0123"
        html_value = testimonials_html({
            "testimonials": [{"kind": "image", "image_src": base64_src}]
        })
        self.assertEqual(html_value.count(base64_src), 1)
        self.assertNotIn('href="' + base64_src, html_value)
        self.assertIn('class="hf6514-testimonial-zoom"', html_value)

    def test_texto_e_video_conservados_sem_texto_inventado(self):
        rendered = testimonials_html({
            "testimonials": [
                {"kind": "text", "name": "Maria", "text": "Ficou perfeito!"},
                {"kind": "video", "name": "Cliente", "video_src": "https://exemplo.invalid/video.mp4",
                 "text": "Recebemos tudo certinho!"},
            ]
        })
        self.assertIn("Ficou perfeito!", rendered)
        self.assertIn("Recebemos tudo certinho!", rendered)
        self.assertIn("video controls", rendered)
        self.assertIn("Maria", rendered)
        self.assertEqual(rendered.count("<dialog"), 0)
        self.assertNotIn("Depoimento enviado pela AlphaFest", rendered)

    def test_escapes_nomes_e_mantem_apenas_imagens_ativas(self):
        cfg = {"testimonials": [
            {"kind": "image", "image_src": "https://exemplo.invalid/a.png",
             "name": '<script>alert(1)</script>', "active": True},
            {"kind": "image", "image_src": "https://exemplo.invalid/b.png", "active": False},
            {"kind": "image", "image_src": "javascript:alert(1)", "active": True},
        ]}
        rendered = testimonials_html(cfg)
        self.assertNotIn("<script>alert(1)</script>", rendered)
        self.assertIn(html.escape('<script>alert(1)</script>'), rendered)
        self.assertIn("https://exemplo.invalid/a.png", rendered)
        self.assertNotIn("https://exemplo.invalid/b.png", rendered)
        self.assertNotIn("javascript:alert(1)", rendered)
        self.assertEqual(rendered.count('class="hf6514-testimonial hf6514-testimonial-image"'), 1)

    def test_sem_depoimentos_nao_monta_secao(self):
        self.assertEqual(testimonials_html({}), "")
        self.assertEqual(testimonials_html({"testimonials": [{"kind":"image","image_src":"https://exemplo.invalid/1.png","active": False}]}), "")

    def test_css_responsivo_sem_recortar_imagem(self):
        self.assertIn("object-fit:contain", HOME_CONTENT_CSS)
        self.assertIn(".hf6514-testimonial-zoom img", HOME_CONTENT_CSS)
        self.assertIn("aspect-ratio:4/5", HOME_CONTENT_CSS)
        self.assertIn("max-width:620px", HOME_CONTENT_CSS)
        self.assertIn(".hf6514-testimonial-dialog::backdrop", HOME_CONTENT_CSS)

    def test_zoom_nativo_com_escape_e_foco_de_volta(self):
        for keyword in ("modal.showModal()", "modal.close()", "focoAnterior.focus()",
                        "ampliada.src=imagem.currentSrc||imagem.src", "Escape"):
            self.assertIn(keyword, HOME_CONTENT_JS)


if __name__ == "__main__":
    unittest.main()
