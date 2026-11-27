"""Testes isolados do guia de conteúdo útil do site AlphaFest."""
import unittest

from site_conteudo_util_service import PERGUNTAS, inject_conteudo_util


class GuiaConteudoUtilTests(unittest.TestCase):
    def setUp(self):
        self.base = '<!doctype html><html><head><title>AlphaFest</title></head><body><main>Produtos</main><footer class="footer">Contato</footer></body></html>'

    def test_insere_guia_e_mantem_rodape(self):
        page = inject_conteudo_util(self.base)
        self.assertIn('id="guia-personalizacao-alphafest"', page)
        self.assertIn('<footer class="footer">Contato</footer>', page)
        self.assertLess(page.index('guia-personalizacao-alphafest'), page.index('<footer class="footer">'))
        self.assertIn('Como escolher balões para um evento?', page)

    def test_idempotencia(self):
        once = inject_conteudo_util(self.base)
        self.assertEqual(once, inject_conteudo_util(once))

    def test_nao_altera_sem_rodape(self):
        self.assertEqual('<html></html>', inject_conteudo_util('<html></html>'))

    def test_conteudo_nao_vazio(self):
        self.assertGreaterEqual(len(PERGUNTAS), 5)
        self.assertTrue(all(title and answer for title, answer in PERGUNTAS))


if __name__ == "__main__":
    unittest.main()
