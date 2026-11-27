"""Teste isolado do SEO local da home AlphaFest; não publica site."""
import json
import re
import unittest

from site_production_service import preparar_html_producao


class SEOLocalItatibaTests(unittest.TestCase):
    def test_meta_e_schema_preservam_corpo_e_layout(self):
        base = (
            '<!doctype html><html lang="pt-BR"><head>'
            '<title>Alphafest · Personalizados &amp; Balões</title>'
            '<meta name="description" content="Texto anterior">'
            '</head><body><main id="loja"><h1>Arte homologada</h1></main></body></html>'
        )
        final = preparar_html_producao(base)
        self.assertIn("<title>Personalizados em Itatiba | AlphaFest", final)
        self.assertIn('name="description" content="AlphaFest: personalizados em Itatiba', final)
        self.assertNotIn("Texto anterior", final)
        self.assertEqual(final.count('<meta name="description"'), 1)
        self.assertIn('<main id="loja"><h1>Arte homologada</h1></main>', final)
        match = re.search(
            r'<script id="alphafest-structured-data" type="application/ld\+json">(.*?)</script>',
            final, re.S
        )
        self.assertIsNotNone(match)
        schema = json.loads(match.group(1))
        loja = next(x for x in schema["@graph"] if x["@type"] == "Store")
        self.assertEqual(loja["address"]["addressLocality"], "Itatiba")
        self.assertEqual(loja["address"]["postalCode"], "13251-530")
        self.assertEqual(loja["telephone"], "+55 11 97294-9533")

    def test_nao_acrescenta_meta_duplicada(self):
        base = '<!doctype html><html><head><title>AlphaFest</title></head><body>Loja</body></html>'
        final = preparar_html_producao(base)
        self.assertEqual(final.count('name="description"'), 1)
        self.assertEqual(final.count("<title>"), 1)


if __name__ == "__main__":
    unittest.main()
