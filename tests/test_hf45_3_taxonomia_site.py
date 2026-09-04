import unittest
from pathlib import Path

from site_vitrine_service import gerar_html_vitrine, resumir_vitrine
from site_completo_service import gerar_html_site_completo


class HF454TaxonomiaSiteTests(unittest.TestCase):
    def _produto(self, nome, categoria, subcategoria=""):
        return {
            "Nome": nome,
            "Categoria": categoria,
            "Subcategoria": subcategoria,
            "Descricao": "Produto personalizado para teste.",
            "Imagens": ["https://example.com/produto.jpg"],
            "PublicarSite": True,
        }

    def test_resumo_taxonomia_usa_categoria_subcategoria_e_contagens(self):
        catalogo = [
            self._produto("Topo 1", "Festas", "Topos de bolo"),
            self._produto("Topo 2", "Festas", "Topos de bolo"),
            self._produto("Tag", "Festas", "Papelaria"),
            self._produto("Caneca", "Brindes", "Canecas"),
            self._produto("Sem sub", "Brindes", ""),
        ]
        resumo = resumir_vitrine(catalogo, usar_taxonomia_catalogo=True)
        self.assertEqual(resumo["categorias"], ["Brindes", "Festas"])
        self.assertEqual(resumo["total_categorias"], 2)
        self.assertEqual(resumo["total_subcategorias"], 4)
        self.assertEqual(resumo["sem_subcategoria"], 1)
        self.assertEqual(resumo["contagem_por_categoria"]["Festas"], 3)
        self.assertEqual(resumo["contagem_por_subcategoria"]["Festas"]["Topos de bolo"], 2)
        self.assertEqual(resumo["subcategorias_por_categoria"]["Festas"], ["Papelaria", "Topos de bolo"])
        self.assertIn("Sem subcategoria", resumo["subcategorias_por_categoria"]["Brindes"])

    def test_html_taxonomia_tem_navegacao_visual_em_duas_etapas(self):
        catalogo = [
            self._produto("Topo 1", "Festas", "Topos de bolo"),
            self._produto("Tag", "Festas", "Papelaria"),
            self._produto("Caneca", "Brindes", "Canecas"),
        ]
        pagina = gerar_html_vitrine(
            catalogo,
            {"whatsapp_catalogo": "11972949533"},
            modo_preview=True,
            usar_taxonomia_catalogo=True,
        )
        self.assertIn("PRÉVIA INTERNA HF45.4", pagina)
        self.assertIn("Escolha uma categoria", pagina)
        self.assertIn("Escolha uma subcategoria", pagina)
        self.assertIn('data-cat="festas"', pagina)
        self.assertIn('data-parent="festas" data-sub="topos-de-bolo"', pagina)
        self.assertIn('data-cat="festas" data-sub="topos-de-bolo"', pagina)
        self.assertIn('id="taxonomy-current"', pagina)
        self.assertIn("c.dataset.sub===sub", pagina)
        self.assertIn("Todas as subcategorias", pagina)
        self.assertIn(">2</b></button>", pagina)  # Festas possui 2 produtos no exemplo

    def test_modo_padrao_preserva_hf44_sem_taxonomia(self):
        catalogo = [self._produto("ADESIVO DTF UV", "ADESIVO DTF UV", "ADESIVOS")]
        pagina = gerar_html_vitrine(catalogo, {}, modo_preview=False)
        self.assertIn('data-cat="grafica-rapida"', pagina)
        self.assertNotIn('id="subfilters"', pagina)
        self.assertNotIn('id="taxonomy-current"', pagina)
        self.assertNotIn("PRÉVIA INTERNA HF45.4", pagina)

    def test_site_completo_aceita_previa_taxonomia_sem_mudar_padrao(self):
        catalogo = [self._produto("Produto", "Categoria Nova", "Sub Nova")]
        novo = gerar_html_site_completo(catalogo, {}, modo_preview=True, usar_taxonomia_catalogo=True)
        antigo = gerar_html_site_completo(catalogo, {}, modo_preview=False)
        self.assertIn("PRÉVIA INTERNA HF45.4", novo)
        self.assertIn("Sub Nova", novo)
        self.assertIn('data-cat="categoria-nova"', novo)
        self.assertNotIn('id="subfilters"', antigo)

    def test_manager_expoe_previa_hf454_e_producao_hf44_continua_sem_flag(self):
        app = Path("app.py").read_text(encoding="utf-8")
        self.assertIn('"🧭 Prévia Categoria → Subcategoria — HF45.4"', app)
        self.assertIn("usar_taxonomia_catalogo=True", app)
        bloco_prod = app.split('# HF44 — publicação assistida no Worker', 1)[1]
        chamada = bloco_prod.split('pacote_producao_hf44 =', 1)[0]
        self.assertNotIn("usar_taxonomia_catalogo=True", chamada)


if __name__ == "__main__":
    unittest.main()
