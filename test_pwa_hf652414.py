"""Testes sem rede para a entrega do app instalavel AlphaFest."""
import io
import json
import zipfile

from site_pwa_service import inject_pwa, pwa_assets
from site_production_service import gerar_pacote_producao
from site_cloudflare_publish_service import extrair_pacote_publico

HTML = '<!doctype html><html lang="pt-BR"><head><title>AlphaFest</title></head><body><h1>Bem-vindo</h1></body></html>'

def test_pwa():
    html = inject_pwa(HTML)
    assert '/manifest.webmanifest' in html and '/sw.js' in html
    assert inject_pwa(html) == html
    manifest = json.loads(pwa_assets()['manifest.webmanifest'])
    assert manifest['display'] == 'standalone'
    assert manifest['start_url'].startswith('/')
    assert {'192x192','512x512'} <= {icon['sizes'] for icon in manifest['icons']}
    assert 'caches.open' in pwa_assets()['sw.js'].decode()
    assert 'cache.put(' not in pwa_assets()['sw.js'].decode()
    package = gerar_pacote_producao(HTML, dicas_content=[])
    with zipfile.ZipFile(io.BytesIO(package)) as z:
        assert z.testzip() is None
        for name in ['index.html','manifest.webmanifest','sw.js','offline.html','android-chrome-192x192.png','android-chrome-512x512.png']:
            assert name in z.namelist(), name
    assets, _ = extrair_pacote_publico(package)
    for name in ['/manifest.webmanifest','/sw.js','/offline.html','/index.html']:
        assert name in assets
    assert 'manifest.webmanifest' in assets['/index.html'].decode()
    print('OK: manifesto, icones, SW, pacote e extracao Cloudflare')

if __name__ == '__main__':
    test_pwa()
