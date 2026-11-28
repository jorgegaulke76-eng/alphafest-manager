"""HF80: visual natalino azul nos mascotes externos, sem alterar dados."""
import base64
import unittest
from site_campaign_service import inject_campaign
from site_mascotes_natal_hf80 import eh_natal_azul, mascote_natal_html, natal_hat_data_uri

HTML = '<!doctype html><html><head><title>AlphaFest</title></head><body><p>Produtos e preços</p></body></html>'

class NatalHF80(unittest.TestCase):
    def test_campanha_natal_exibe_dois_mascotes_com_acessorios_azuis(self):
        cfg = {"enabled":True, "campaign_name":"Natal na AlphaFest", "image_src":"https://example.com/natal.webp", "show_mascots":True}
        pagina = inject_campaign(HTML, cfg, {"whatsapp_catalogo":"11972949533"})
        self.assertIn('afc65-thu afc65-mascot-natal', pagina)
        self.assertIn('afc65-fox afc65-mascot-natal', pagina)
        self.assertEqual(pagina.count('afc65-natal-hat'), 4) # duas tags + estilo
        self.assertIn('width:min(370px,31vw)', pagina)
        self.assertIn('Produtos e preços', pagina)
        self.assertIn('afc65-cta', pagina)
        self.assertIn('Fechar campanha', pagina)

    def test_campanha_nao_natal_preserva_mascotes_originais(self):
        self.assertFalse(eh_natal_azul({"campaign_name":"Novembro Azul"}))
        page = inject_campaign(HTML, {"enabled":True, "campaign_name":"Novembro Azul", "image_src":"https://example.com/teste.webp"}, {})
        self.assertNotIn('afc65-mascot-natal', page)
        self.assertNotIn('afc65-natal-hat', page)

    def test_sem_mascotes_nao_cria_imagens_externas(self):
        page = inject_campaign(HTML, {"enabled":True, "campaign_name":"Natal", "show_mascots":False, "image_src":"https://example.com/natal.webp"}, {})
        self.assertNotIn('afc65-mascot-base', page)

    def test_svg_valido_pequeno_e_sem_vermelho(self):
        src = natal_hat_data_uri()
        svg = base64.b64decode(src.split(",",1)[1]).decode()
        self.assertTrue(svg.startswith("<svg"))
        self.assertLess(len(svg),5000)
        self.assertNotIn("#FF0000",svg)
        self.assertIn("#0058D8",svg)
        self.assertIn('afc65-thu', mascote_natal_html('thu', 'data:image/webp;base64,AA==','Thu'))
        self.assertEqual(mascote_natal_html('outro','imagem','outro'),'')

if __name__ == '__main__':
    unittest.main()
