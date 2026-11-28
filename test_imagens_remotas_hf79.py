"""HF79 - teste de imagens publicas usando bytes ficticios e sem rede."""
import io
import unittest
from PIL import Image

from site_imagens_remotas_hf79 import (
    _permitida, otimizar_imagens_remotas_hf79, _variantes,
)


def foto_teste():
    # Arte sintética com grande área uniforme, sem informações de clientes.
    img = Image.new("RGB", (1800, 1200), (18, 92, 170))
    buf = io.BytesIO()
    img.save(buf, format="PNG", compress_level=0)
    return buf.getvalue()


class ImagensRemotasHF79(unittest.TestCase):
    def setUp(self):
        self.url = "https://exemplo.supabase.co/storage/v1/object/public/catalogo/banner.png"
        self.dados = foto_teste()

    def test_aceita_apenas_arquivo_publico_de_catalogo(self):
        self.assertTrue(_permitida(self.url))
        for url in (
            "https://evil.example/arquivo.png",
            "http://exemplo.supabase.co/storage/v1/object/public/catalogo/a.png",
            "https://exemplo.supabase.co/storage/v1/object/sign/catalogo/a.png",
            "https://exemplo.supabase.co/storage/v1/object/public/outro/a.png",
            "https://exemplo.supabase.co/storage/v1/object/public/catalogo/a.png?token=privado",
            "https://exemplo.supabase.co.evil.test/storage/v1/object/public/catalogo/a.png",
        ):
            with self.subTest(url=url):
                self.assertFalse(_permitida(url))

    def test_banner_reduzido_sem_alterar_arquivo_original(self):
        html = ('<section class="hf6514-banner"><img src="' + self.url +
                '" alt="Banner informativo AlphaFest" loading="lazy"></section>'
                '<p>Mensagem e preco original permanecem intactos</p>')
        calls = []
        def fake_download(url):
            calls.append(url)
            return self.dados
        pagina, arquivos, rel = otimizar_imagens_remotas_hf79(html, {}, baixar=fake_download)
        self.assertEqual(calls, [self.url])
        self.assertEqual(rel["imagens_otimizadas"], 1)
        self.assertIn('fetchpriority="high"', pagina)
        self.assertIn('loading="eager"', pagina)
        self.assertIn('assets/img/', pagina)
        self.assertIn("Mensagem e preco original permanecem intactos", pagina)
        self.assertTrue(arquivos)
        self.assertEqual(len(self.dados), rel["bytes_originais"])
        with Image.open(io.BytesIO(next(iter(arquivos.values())))) as img:
            self.assertLessEqual(img.width, 1280)

    def test_erro_de_download_preserva_html(self):
        html = '<img src="' + self.url + '" alt="Banner informativo AlphaFest">'
        novo, arquivos, rel = otimizar_imagens_remotas_hf79(html, {}, baixar=lambda _: None)
        self.assertEqual(novo, html)
        self.assertEqual(arquivos, {})
        self.assertEqual(rel["imagens_otimizadas"], 0)

    def test_falha_no_primeiro_produto_nao_impede_proximo(self):
        ruim = self.url.replace("banner.png", "falha.png")
        html = ('<img class="hf50-carousel-product-img" src="' + ruim + '">'
                '<img class="hf50-carousel-product-img" src="' + self.url + '">')
        chamadas = []
        def baixar(url):
            chamadas.append(url)
            return None if url == ruim else self.dados
        novo, arquivos, rel = otimizar_imagens_remotas_hf79(
            html, {}, baixar=baixar)
        self.assertEqual(chamadas, [ruim, self.url])
        self.assertEqual(rel["falhas_download"], 1)
        self.assertEqual(rel["imagens_otimizadas"], 1)
        self.assertIn("assets/img/", novo)
        self.assertTrue(arquivos)

    def test_tres_banners_e_campanha_podem_ser_otimizados(self):
        urls = [self.url.replace("banner.png", f"banner-{i}.png") for i in range(4)]
        campanha = self.url.replace("banner.png", "campanha.png")
        html = ''.join(
            '<img src="' + url + '" alt="Banner informativo AlphaFest" loading="lazy">'
            for url in urls
        ) + '<img class="hf65-art" src="' + campanha + '" alt="Campanha especial AlphaFest">'
        chamadas = []
        def carregar(url):
            chamadas.append(url)
            return self.dados
        novo, assets, rel = otimizar_imagens_remotas_hf79(html, {}, baixar=carregar)
        self.assertEqual(rel["imagens_otimizadas"], 4)
        self.assertEqual(len(chamadas), 4)
        self.assertIn(urls[-1], novo)
        self.assertNotIn(urls[0], novo)
        self.assertNotIn(campanha, novo)
        self.assertTrue(assets)

    def test_maximo_uma_imagem_por_categoria(self):
        html = ''.join('<img class="hf50-carousel-product-img" src="' + self.url +
                       '" alt="Produto ' + str(i) + '">' for i in range(8))
        chamadas = []
        novo, arquivos, rel = otimizar_imagens_remotas_hf79(
            html, {}, baixar=lambda url: (chamadas.append(url) or self.dados))
        self.assertEqual(len(chamadas), 1)
        self.assertEqual(rel["imagens_otimizadas"], 1)
        self.assertEqual(novo.count(self.url), 7)


if __name__ == "__main__":
    unittest.main()
