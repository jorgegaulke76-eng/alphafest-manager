import unittest
from pathlib import Path

from site_vitrine_service import selecionar_produtos_vitrine, resumir_vitrine, gerar_html_vitrine

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")


class HF36SiteVitrineTests(unittest.TestCase):
    def setUp(self):
        self.catalogo = [
            {
                "Nome": "Topo Premium",
                "Categoria": "Topo de Bolo",
                "Descricao": "Topo personalizado para festas.",
                "Imagens": ["https://example.com/topo.jpg"],
                "Preco": "25,00",
                "PublicarSite": True,
                "Destaque": True,
                "ExibirPrecoSite": True,
                "Variacoes": ["Rosa", "Azul"],
            },
            {
                "Nome": "Bubble Festa",
                "Categoria": "Balões",
                "Descricao": "Bubble personalizado.",
                "Imagens": ["https://example.com/bubble.jpg"],
                "PublicarSite": True,
            },
            {
                "Nome": "Produto interno",
                "Categoria": "Interno",
                "Descricao": "Não deve ir para a vitrine.",
                "Imagens": ["https://example.com/interno.jpg"],
                "PublicarSite": False,
            },
            {
                "Nome": "Marcado incompleto",
                "Categoria": "Teste",
                "Descricao": "",
                "Imagens": [],
                "PublicarSite": True,
            },
        ]

    def test_seleciona_apenas_marcados_prontos_sem_mutar_catalogo(self):
        antes = [dict(x) for x in self.catalogo]
        itens = selecionar_produtos_vitrine(self.catalogo)
        self.assertEqual([x["nome"] for x in itens], ["Topo Premium", "Bubble Festa"])
        self.assertEqual(self.catalogo, antes)

    def test_resumo_separa_produtos_categorias_e_destaques(self):
        resumo = resumir_vitrine(self.catalogo)
        self.assertEqual(resumo["total"], 2)
        self.assertEqual(resumo["destaques"], 1)
        self.assertEqual(resumo["total_categorias"], 2)

    def test_html_tem_busca_filtros_responsivos_e_whatsapp(self):
        html = gerar_html_vitrine(
            self.catalogo,
            {
                "nome": "AlphaFest",
                "subtitulo": "Personalizados & Balões",
                "slogan": "O poder de estar presente em cada presente!",
                "whatsapp_catalogo": "11999998888",
                "cidade": "Itatiba",
                "uf": "SP",
            },
            logo_src="data:image/png;base64,abc",
        )
        self.assertIn("PRÉVIA INTERNA HF40", html)
        self.assertIn('id="search"', html)
        self.assertIn('data-cat="todos"', html)
        self.assertIn("@media(max-width:620px)", html)
        self.assertIn("Topo Premium", html)
        self.assertIn("Bubble Festa", html)
        self.assertNotIn("Produto interno", html)
        self.assertNotIn("Marcado incompleto", html)
        self.assertIn("https://wa.me/5511999998888", html)
        self.assertIn("R$ 25,00", html)
        self.assertNotIn("Sob consulta", html)


    def test_preview_nao_expoe_caminho_local_quando_imagem_nao_resolve(self):
        catalogo = [{
            "Nome": "Arquivo local", "Categoria": "Teste", "Descricao": "ok",
            "Imagens": ["/dados/privados/foto.jpg"], "PublicarSite": True,
        }]
        pagina = gerar_html_vitrine(
            catalogo, {"nome": "AlphaFest"}, imagem_resolver=lambda _: ""
        )
        self.assertNotIn("/dados/privados/foto.jpg", pagina)
        self.assertIn("placeholder", pagina)

    def test_app_exibe_preview_desktop_e_celular_sem_publicar(self):
        trecho = APP.split('if pagina_atual == "site":', 1)[1].split('if pagina_atual == "crescimento":', 1)[0]
        self.assertIn('"🌐 Site completo — prévia HF40"', trecho)
        self.assertIn('["🖥️ Desktop", "📱 Celular"]', trecho)
        self.assertIn('_site_gerar_html_completo(', trecho)
        self.assertIn('components.html(html_vitrine_hf36', trecho)
        self.assertIn('"⬇️ Baixar esta prévia HTML"', trecho)
        self.assertIn("o site oficial já está migrado", trecho)
        self.assertNotIn("publish_catalog_html(", trecho)


if __name__ == "__main__":
    unittest.main()
