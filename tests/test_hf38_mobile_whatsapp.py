import unittest
from pathlib import Path
from urllib.parse import unquote

from site_vitrine_service import gerar_html_vitrine

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")


class HF38MobileWhatsappTests(unittest.TestCase):
    def _catalogo(self):
        return [{
            "Nome": "Topo Personalizado",
            "Categoria": "Topo de Bolo",
            "Descricao": "Produzido sob medida.",
            "Imagens": ["https://example.com/topo.jpg"],
            "PublicarSite": True,
            "Preco": "25,00",
            "ExibirPrecoSite": False,
        }]

    def _empresa(self):
        return {"nome": "AlphaFest", "whatsapp_catalogo": "11999998888"}

    def test_whatsapp_do_produto_leva_contexto_de_orcamento(self):
        pagina = gerar_html_vitrine(self._catalogo(), self._empresa())
        decodificada = unquote(pagina)
        self.assertIn("orçamento para: Topo Personalizado", decodificada)
        self.assertIn("tamanho/personalização, cor, quantidade, material e prazo", decodificada)
        self.assertIn('aria-label="Pedir orçamento de Topo Personalizado pelo WhatsApp"', pagina)

    def test_mobile_tem_cta_fixo_e_layout_touch(self):
        pagina = gerar_html_vitrine(self._catalogo(), self._empresa())
        self.assertIn('class="mobile-whatsapp"', pagina)
        self.assertIn("position:fixed", pagina)
        self.assertIn("min-height:52px", pagina)
        self.assertIn("-webkit-line-clamp:4", pagina)
        self.assertIn("body{padding-bottom:76px}", pagina)

    def test_hf38_preserva_preco_opcional(self):
        pagina = gerar_html_vitrine(self._catalogo(), self._empresa())
        self.assertNotIn("R$ 25,00", pagina)
        com_preco = self._catalogo()
        com_preco[0]["ExibirPrecoSite"] = True
        pagina_preco = gerar_html_vitrine(com_preco, self._empresa())
        self.assertIn("R$ 25,00", pagina_preco)

    def test_app_continua_preview_sem_publicacao(self):
        trecho = APP.split('if pagina_atual == "site":', 1)[1].split('if pagina_atual == "crescimento":', 1)[0]
        self.assertIn('"🌐 Nova vitrine pública — prévia HF39"', trecho)
        self.assertIn('["🖥️ Desktop", "📱 Celular"]', trecho)
        self.assertIn('alphafest-vitrine-preview-hf39.html', trecho)
        self.assertNotIn('publish_catalog_html(', trecho)


if __name__ == "__main__":
    unittest.main()
