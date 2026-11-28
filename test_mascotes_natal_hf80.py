"""HF80: troca real de mascotes no pop-up Natal Azul."""
import base64
import re
import unittest
from pathlib import Path

from site_campaign_service import inject_campaign
from site_mascotes_natal_hf80 import eh_natal_azul

HTML = '<!doctype html><html><head><title>AlphaFest</title></head><body><p>Produtos e preços</p></body></html>'
ROOT = Path(__file__).resolve().parent


class NatalHF80(unittest.TestCase):
    def test_mascotes_reais_leves_transparentes_presentes(self):
        for filename in ("thu_natal_azul.webp", "fox_natal_azul.webp"):
            data = (ROOT / "assets" / "mascotes" / filename).read_bytes()
            self.assertLess(len(data), 100_000)
            self.assertTrue(data.startswith(b"RIFF"))
            self.assertEqual(data[8:12], b"WEBP")
            self.assertIn(b"VP8X", data[:20])

    def test_natal_exibe_arqivos_reais_sem_gorro_sobreposto(self):
        cfg = {"enabled":True, "campaign_name":"Natal na AlphaFest", "image_src":"https://example.com/natal.webp", "show_mascots":True}
        page = inject_campaign(HTML, cfg, {"whatsapp_catalogo":"11972949533"})
        self.assertIn('class="afc65-mascot afc65-thu"', page)
        self.assertIn('class="afc65-mascot afc65-fox"', page)
        self.assertNotIn('afc65-natal-hat', page)
        self.assertNotIn('afc65-mascot-natal', page)
        imgs = re.findall(r'<img class="afc65-mascot afc65-(thu|fox)" src="data:image/webp;base64,([A-Za-z0-9+/=]+)"', page)
        self.assertEqual(len(imgs), 2)
        for name, data in imgs:
            raw = base64.b64decode(data, validate=True)
            self.assertEqual(raw, (ROOT/"assets"/"mascotes"/f"{name}_natal_azul.webp").read_bytes())
        self.assertIn("Produtos e preços", page)
        self.assertIn('afc65-cta', page)
        self.assertIn('Fechar campanha', page)

    def test_novembro_usa_mascotes_originais(self):
        self.assertFalse(eh_natal_azul({"campaign_name":"Novembro Azul"}))
        page = inject_campaign(HTML, {"enabled":True, "campaign_name":"Novembro Azul", "image_src":"https://example.com/teste.webp"}, {})
        self.assertIn('class="afc65-mascot afc65-thu"', page)
        self.assertIn('class="afc65-mascot afc65-fox"', page)
        self.assertNotIn('afc65-natal-hat', page)
        self.assertNotIn('data:image/svg+xml;base64,', page)

    def test_desabilitar_mascotes_funciona(self):
        page = inject_campaign(HTML, {"enabled":True, "campaign_name":"Natal", "show_mascots":False, "image_src":"https://example.com/natal.webp"}, {})
        self.assertNotIn('class="afc65-mascot afc65-thu"', page)
        self.assertNotIn('class="afc65-mascot afc65-fox"', page)

if __name__ == '__main__':
    unittest.main()
