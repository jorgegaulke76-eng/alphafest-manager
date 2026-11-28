"""HF81: testes sem rede e sem fotos de clientes."""
from __future__ import annotations

import io
import re
import unittest
from PIL import Image
from site_mobile_imagens_hf81 import otimizar_imagens_mobile_hf81
from site_campaign_service import inject_campaign

URL = "https://exemplo.supabase.co/storage/v1/object/public/catalogo/banner.png"


def sample(width=2000, height=900):
    imagem = Image.new("RGB", (width, height), (14, 116, 212))
    out = io.BytesIO()
    imagem.save(out, format="PNG", compress_level=0)
    return out.getvalue()


class SiteMobileHF81(unittest.TestCase):
    def setUp(self):
        self.image = sample()

    def test_banner_com_picture_mobile_sem_trocar_src_desktop(self):
        html = (
            '<section class="hf6514-banner"><article class="hf6514-banner-slide">'
            '<img src="' + URL + '" alt="Banner informativo AlphaFest" loading="eager">'
            '</article></section>'
        )
        result, assets, diag = otimizar_imagens_mobile_hf81(
            html, {}, baixar=lambda u: self.image
        )
        self.assertEqual(diag["banners_mobile"], 1)
        self.assertIn('<picture class="hf81-banner-media"', result)
        self.assertIn('media="(max-width: 700px)"', result)
        self.assertNotIn('fetchpriority="high"', result)  # banner abaixo da dobra
        self.assertIn('src="' + URL + '"', result)
        self.assertIn('width="2000"', result)
        self.assertIn('height="900"', result)
        self.assertTrue(any(k.endswith(".webp") for k in assets))
        with Image.open(io.BytesIO(next(iter(assets.values())))) as mobile:
            self.assertLessEqual(mobile.width, 720)
            self.assertEqual(mobile.height, 324)

    def test_popup_responsivo_sem_mudar_arte_original(self):
        html = '<div class="afc65-card"><img class="afc65-art" src="' + URL + '" alt="Campanha especial AlphaFest"></div>'
        new, assets, status = otimizar_imagens_mobile_hf81(html, {}, baixar=lambda u:self.image)
        self.assertEqual(status["popup_mobile"], 1)
        self.assertIn("hf81-popup-media", new)
        self.assertIn('fetchpriority="high"', new)
        self.assertIn('src="' + URL + '"', new)
        self.assertIn("data-hf81-mobile", new)
        self.assertTrue(assets)
        with Image.open(io.BytesIO(next(iter(assets.values())))) as img:
            self.assertEqual(img.width, 600)

    def test_seis_banners_e_um_popup_sem_prioridade_dos_banners(self):
        urls = [URL.replace("banner.png", f"banner-{n}.png") for n in range(7)]
        pagina = "".join(
            f'<img src="{url}" alt="Banner informativo AlphaFest" loading="lazy">'
            for url in urls
        )
        pagina += '<img class="afc65-art" src="' + URL + '" alt="Campanha especial AlphaFest">'
        resultado, arquivos, diagnostico = otimizar_imagens_mobile_hf81(
            pagina, {}, baixar=lambda u: self.image
        )
        self.assertEqual(diagnostico["banners_mobile"], 6)
        self.assertEqual(diagnostico["popup_mobile"], 1)
        self.assertIn(urls[-1], resultado)
        self.assertEqual(resultado.count('fetchpriority="high"'), 1)
        self.assertEqual(resultado.count('<picture'), 7)
        self.assertTrue(arquivos)

    def test_arquivo_local_gerado_hf79_tambem_fica_responsivo(self):
        local = "assets/img/" + "a"*24 + ".png"
        html = '<img src="/' + local + '" alt="Banner informativo AlphaFest">'
        new, assets, status = otimizar_imagens_mobile_hf81(html, {local:self.image})
        self.assertEqual(status["banners_mobile"], 1)
        self.assertIn('src="/' + local + '"', new)
        self.assertEqual(assets[local], self.image)
        self.assertEqual(len(assets),2)

    def test_url_externa_nao_publica_ou_falha_de_download_preserva_original(self):
        bad = "https://example.com/private.png"
        html = '<img class="afc65-art" src="' + bad + '" alt="Campanha especial AlphaFest">'
        called = []
        new, assets, status = otimizar_imagens_mobile_hf81(html, {}, baixar=lambda u: called.append(u))
        self.assertEqual(new, html)
        self.assertEqual(assets,{})
        self.assertEqual(called,[])
        self.assertEqual(status["popup_mobile"],0)

    def test_dois_processamentos_nao_duplicam_picture(self):
        html = '<img src="' + URL + '" alt="Banner informativo AlphaFest">'
        first, assets, _ = otimizar_imagens_mobile_hf81(html, {}, baixar=lambda u:self.image)
        second, _, _ = otimizar_imagens_mobile_hf81(first, assets, baixar=lambda u:self.image)
        self.assertEqual(second.count('<picture'),1)

    def test_popup_padrao_abre_imediato_somente_no_mobile(self):
        pagina = inject_campaign(
            "<html><head></head><body><h1>AlphaFest</h1></body></html>",
            {"enabled": True, "campaign_name": "Natal na AlphaFest",
             "image_src": "https://example.com/natal.webp",
             "show_mascots": False}, {},
        )
        self.assertIn("const fastMobile=!!(", pagina)
        self.assertIn("C.delay===2000", pagina)
        self.assertIn("max-width: 700px", pagina)
        self.assertIn("if(fastMobile) show(); else setTimeout(show,C.delay);", pagina)
        self.assertIn("afc65-fast-mobile", pagina)
        self.assertIn('fetchpriority="high"', pagina)
        self.assertIn("function markSeen()", pagina)
        self.assertIn("setTimeout(hide,C.duration)", pagina)

    def test_atraso_personalizado_permanece_configurado(self):
        pagina = inject_campaign(
            "<html><head></head><body></body></html>",
            {"enabled": True, "delay_seconds": 7,
             "image_src": "https://example.com/campanha.webp",
             "show_mascots": False}, {},
        )
        self.assertIn('"delay": 7000', pagina)
        self.assertIn("C.delay===2000", pagina)
        self.assertIn("else setTimeout(show,C.delay)", pagina)

    def test_legenda_de_novembro_sai_somente_no_natal(self):
        html = "<html><head></head><body><h1>AlphaFest</h1></body></html>"
        natal = inject_campaign(html, {
            "enabled":True, "campaign_name":"Natal na AlphaFest",
            "image_src": "https://example.com/natal.webp",
            "headline":"NATAL NA ALPHAFEST", "message":"NOVEMBRO AZUL",
            "show_mascots":False,
        },{})
        self.assertNotIn("NOVEMBRO AZUL", natal)
        self.assertIn("NATAL NA ALPHAFEST", natal)
        outro = inject_campaign(html, {
            "enabled":True, "campaign_name":"Novembro Azul",
            "image_src":"https://example.com/novembro.webp",
            "message":"NOVEMBRO AZUL", "show_mascots":False
        },{})
        self.assertIn("NOVEMBRO AZUL", outro)

if __name__ == "__main__":
    unittest.main()
