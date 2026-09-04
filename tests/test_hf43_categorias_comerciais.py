import io
import json
import unittest
import zipfile
from pathlib import Path

from site_vitrine_service import (
    categoria_comercial_produto,
    gerar_html_vitrine,
    resumir_vitrine,
    selecionar_produtos_vitrine,
)
from site_completo_service import gerar_html_site_completo
from site_production_service import gerar_pacote_producao


class HF43CategoriasComerciaisTests(unittest.TestCase):
    def _produto(self, nome, categoria, descricao="Personalizado sob medida.", **extra):
        p = {
            "Nome": nome,
            "Categoria": categoria,
            "Descricao": descricao,
            "Imagens": [f"https://example.com/{nome[:5]}.jpg"],
            "PublicarSite": True,
        }
        p.update(extra)
        return p

    def _catalogo_realista(self):
        return [
            self._produto("ADESIVO DTF UV", "ADESIVO DTF UV"),
            self._produto("BANDEIROLA TECIDO COM BORDA", "BRINDE / DECORATIVO"),
            self._produto("BUBBLE 55 cm COM BASE DE BALÕES", "BUBBLE"),
            self._produto("CANECA PORCELANA PERSONALIZADA", "CANECAS PORCELANA COM ALÇA"),
            self._produto("COPO LONG DRINK NEOM", "COPOS"),
            self._produto("CAIXA CONE", "LEMBRANÇA"),
            self._produto("ECOBAG", "LEMBRANÇA"),
            self._produto("PAPELARIA PARA SACOLA PVC", "PAPELARIA"),
            self._produto("SACO 10X15 METALIZADO PERSONALIZADO", "PAPELARIA"),
            self._produto("TOPO DE BOLO CAMADAS", "TOPO DE BOLO"),
            self._produto("TOPO FLORK SIMPLES", "TOPO DE BOLO"),
            self._produto("MEDALHA PERSONALIZADA SIMPLES", "TROFÉU"),
            self._produto("TROFEU 3D PERSONALIZADO", "TROFÉU"),
            self._produto("TROFÉU 3D MINI PERSONALIZADO", "TROFÉU"),
            self._produto("PAPEL DE ARROZ", "PAPEL DE ARROZ"),
            self._produto("Vela Personalizada 3D - Buzz Lightyear", "Vela Personalizada 3D"),
        ]

    def test_agrupamento_comercial_nao_muta_categoria_oficial(self):
        catalogo = self._catalogo_realista()
        antes = [dict(x) for x in catalogo]
        itens = selecionar_produtos_vitrine(catalogo)
        por_nome = {x["nome"]: x for x in itens}
        self.assertEqual(por_nome["BUBBLE 55 cm COM BASE DE BALÕES"]["categoria_comercial"], "Balões & Decoração")
        self.assertEqual(por_nome["CANECA PORCELANA PERSONALIZADA"]["categoria_comercial"], "Brindes")
        self.assertEqual(por_nome["ADESIVO DTF UV"]["categoria_comercial"], "Gráfica Rápida")
        self.assertEqual(por_nome["CAIXA CONE"]["categoria_comercial"], "Convites & Papelaria")
        self.assertEqual(por_nome["TOPO DE BOLO CAMADAS"]["categoria_comercial"], "Festas & Personalizados")
        self.assertEqual(por_nome["TROFEU 3D PERSONALIZADO"]["categoria_comercial"], "Impressão 3D")
        self.assertEqual(catalogo, antes)

    def test_efeito_3d_visual_nao_confunde_topo_com_impressao_3d(self):
        item = {
            "nome": "Topo de Bolo Camadas",
            "categoria": "Topo de Bolo",
            "descricao": "Scrap em camadas com efeito 3D de sobreposição.",
        }
        self.assertEqual(categoria_comercial_produto(item), "Festas & Personalizados")

    def test_gravacao_laser_e_kits_entram_quando_existirem(self):
        laser = {"nome": "Chaveiro gravado a laser", "categoria": "Brinde", "descricao": "laser"}
        kit = {"nome": "Kit festa completo", "categoria": "Festa", "descricao": "composição de festa"}
        self.assertEqual(categoria_comercial_produto(laser), "Gravação a Laser")
        self.assertEqual(categoria_comercial_produto(kit), "Kits Festa")

    def test_resumo_exibe_so_categorias_com_produto_e_em_ordem_comercial(self):
        r = resumir_vitrine(self._catalogo_realista())
        self.assertEqual(r["total"], 16)
        self.assertEqual(r["categorias"], [
            "Festas & Personalizados",
            "Balões & Decoração",
            "Gráfica Rápida",
            "Brindes",
            "Convites & Papelaria",
            "Impressão 3D",
        ])
        self.assertEqual(r["total_categorias"], 6)
        self.assertNotIn("Gravação a Laser", r["categorias"])
        self.assertNotIn("Kits Festa", r["categorias"])

    def test_html_filtra_por_categoria_comercial_e_todos_continua_disponivel(self):
        pagina = gerar_html_vitrine(self._catalogo_realista(), {"whatsapp_catalogo": "11972949533"}, modo_preview=False)
        self.assertIn('data-cat="todos">Todos</button>', pagina)
        self.assertIn('data-cat="festas-personalizados">Festas &amp; Personalizados</button>', pagina)
        self.assertIn('data-cat="baloes-decoracao">Balões &amp; Decoração</button>', pagina)
        self.assertIn('data-cat="grafica-rapida">Gráfica Rápida</button>', pagina)
        self.assertIn('data-cat="brindes">Brindes</button>', pagina)
        self.assertIn('data-cat="convites-papelaria">Convites &amp; Papelaria</button>', pagina)
        self.assertIn('data-cat="impressao-3d">Impressão 3D</button>', pagina)
        self.assertNotIn('data-cat="adesivo-dtf-uv">ADESIVO DTF UV</button>', pagina)
        self.assertIn('class="product-card" data-cat="grafica-rapida"', pagina)
        self.assertIn('class="product-card" data-cat="baloes-decoracao"', pagina)
        self.assertIn("cat==='todos'||c.dataset.cat===cat", pagina)
        self.assertIn("6</strong><span>categorias comerciais", pagina)

    def test_busca_preserva_categoria_interna_sem_exibi_la_como_filtro(self):
        pagina = gerar_html_vitrine([
            self._produto("Produto Especial", "Categoria Interna Antiga", descricao="Topo de bolo especial")
        ], {}, modo_preview=False)
        self.assertIn("categoria interna antiga", pagina)
        self.assertNotIn('>Categoria Interna Antiga</button>', pagina)
        self.assertIn('>Festas &amp; Personalizados</button>', pagina)

    def test_pacote_producao_hf43_carrega_categorias_comerciais_sem_dns(self):
        pagina = gerar_html_site_completo(self._catalogo_realista(), {"nome": "AlphaFest"}, modo_preview=False)
        data = gerar_pacote_producao(pagina, total_produtos=16, versao_manager="20.4.9-I8.13.5-HF43")
        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            index = zf.read("index.html").decode("utf-8")
            status = json.loads(zf.read("STATUS-PRODUCAO.json").decode("utf-8"))
            self.assertIn("Festas &amp; Personalizados", index)
            self.assertIn("Balões &amp; Decoração", index)
            self.assertNotIn("SITE PARALELO HF40", index)
            self.assertEqual(status["versao_manager"], "20.4.9-I8.13.5-HF43")
            self.assertNotIn("CNAME", zf.namelist())

    def test_manager_expoe_hf43_sem_criar_segunda_fonte(self):
        app = Path("app.py").read_text(encoding="utf-8")
        self.assertIn("HF43 · Categorias comerciais", app)
        self.assertIn('"🚀 Produção oficial — HF44"', app)
        self.assertIn("alphafest-site-producao-hf44.zip", app)
        self.assertIn('versao_manager="20.4.9-I8.13.5-HF44"', app)
        self.assertNotIn('save_document("site_categoria', app)


if __name__ == "__main__":
    unittest.main()
