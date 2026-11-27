"""Contratos isolados do validador ZIP oficial HF59, com dados 100% ficticios."""
import io
import json
import unittest
import zipfile

from scripts.hf59_verificar_zip_oficial import auditar


def pacote_teste(*, produtos=92, versao="20.4.9-I8.13.5-HF59",
                 retirar=(), marcador="", imagens=4):
    botoes = "".join(
        '<button class="hf6514-testimonial-zoom">'
        f'<img src="https://example.invalid/ficticio-{i}.jpeg" alt="Teste"></button>'
        for i in range(imagens)
    )
    html = (
        '<!doctype html><html><head><meta name="robots" content="index,follow"></head>'
        '<body><h2>O carinho dos nossos clientes</h2>'
        '<p>Cada mensagem que recebemos e importante.</p>'
        f'<div id="depoimentos">{botoes}</div>'
        '<dialog class="hf6514-testimonial-dialog">'
        '<img class="hf6514-testimonial-full"></dialog>'
        '<div class="hf50-mobile-more"></div>'
        f'{marcador}</body></html>'
    ).encode("utf-8")
    d = {
        "index.html": html,
        "404.html": html,
        "robots.txt": b"User-agent: *\nAllow: /",
        "sitemap.xml": b"<urlset/>",
        "manifest.webmanifest": b"{}",
        "sw.js": b"// ficticio",
        "_headers": b"/*\n X-Content-Type-Options: nosniff",
        "STATUS-PRODUCAO.json": json.dumps({
            "dominio_final": "alphafest.com.br",
            "produtos_snapshot": produtos,
            "versao_manager": versao,
        }).encode(),
    }
    for k in retirar:
        d.pop(k, None)
    with io.BytesIO() as output:
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for nome, dados in d.items():
                z.writestr(nome, dados)
        return output.getvalue()


class TesteZIPOficialHF59(unittest.TestCase):
    def test_pacote_estruturalmente_valido(self):
        result = auditar(pacote_teste())
        self.assertEqual(result["depoimentos_imagem"], 4)
        self.assertEqual(result["produtos_snapshot"], 92)
        self.assertFalse(result["publicacao"])
        self.assertEqual(len(result["sha256_zip"]), 64)

    def test_nao_aceita_catalogo_vazio(self):
        with self.assertRaisesRegex(ValueError, "Catalogo vazio"):
            auditar(pacote_teste(produtos=0))

    def test_nao_aceita_zip_incompleto(self):
        with self.assertRaisesRegex(ValueError, "obrigatorios"):
            auditar(pacote_teste(retirar=("sw.js",)))

    def test_nao_aceita_preview(self):
        with self.assertRaisesRegex(ValueError, "previa/teste"):
            auditar(pacote_teste(versao="HF59-AUDITORIA-LOCAL"))

    def test_nao_aceita_hf52_preview(self):
        with self.assertRaisesRegex(ValueError, "previa/teste"):
            auditar(pacote_teste(marcador="__HF52_PREVIEW_EVENTS"))

    def test_nao_aceita_depoimentos_incompletos(self):
        with self.assertRaisesRegex(ValueError, "Galeria contem"):
            auditar(pacote_teste(imagens=3))


if __name__ == "__main__":
    unittest.main()
