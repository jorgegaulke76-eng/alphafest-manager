"""HF65.24.14: instalacao segura do site AlphaFest como PWA.

Mantem navegacao e catalogo sempre online. O service worker nao memoriza paginas
nem dados do cliente; oferece somente um aviso offline e icones de instalacao.
"""
from __future__ import annotations

import json

MANIFEST = {
    "id": "https://alphafest.com.br/",
    "name": "AlphaFest - Personalizados e Balões",
    "short_name": "AlphaFest",
    "description": "Festas, balões, personalizados, gráfica e brindes em Itatiba.",
    "lang": "pt-BR",
    "dir": "ltr",
    "start_url": "/?origem=app",
    "scope": "/",
    "display": "standalone",
    "background_color": "#ffffff",
    "theme_color": "#087ed3",
    "icons": [
        {"src": "/android-chrome-192x192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "/android-chrome-512x512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
    ],
    "categories": ["shopping", "business"],
    "prefer_related_applications": False,
}

# Sem cache de HTML, pesquisa, carrinho, eventos ou informacoes do visitante.
# Em caso de falha de rede, exibe somente uma pagina informativa.
SERVICE_WORKER = r'''/* AlphaFest PWA: navegação sempre online; não armazenar dados pessoais. */
const VERSION = 'alphafest-offline-hf65-24-14';
const OFFLINE_URL = '/offline.html';
self.addEventListener('install', event => {
  event.waitUntil(caches.open(VERSION).then(cache => cache.add(OFFLINE_URL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('alphafest-offline-') && key !== VERSION).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.mode !== 'navigate' || request.method !== 'GET') return;
  if (new URL(request.url).origin !== self.location.origin) return;
  event.respondWith(fetch(request).catch(async () => (await caches.match(OFFLINE_URL)) || Response.error()));
});
'''

OFFLINE_HTML = '''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#087ed3"><title>AlphaFest - sem conexão</title><style>body{margin:0;background:#eef8ff;color:#123a60;font:16px/1.5 system-ui,Arial;display:grid;min-height:100vh;place-items:center;text-align:center;padding:24px;box-sizing:border-box}main{max-width:440px;background:#fff;border-radius:24px;padding:36px 26px;box-shadow:0 12px 35px #0c4b821a}img{width:92px;height:92px;object-fit:contain}a{display:inline-block;background:#087ed3;color:white;padding:12px 22px;border-radius:999px;text-decoration:none;font-weight:700}</style></head><body><main><img src="/android-chrome-192x192.png" alt="AlphaFest"><h1>Você está sem conexão</h1><p>O aplicativo AlphaFest precisa de internet para mostrar produtos, preços e novidades atualizados.</p><a href="/">Tentar novamente</a></main></body></html>'''

PWA_HEAD_TAGS = (
    '<link rel="manifest" href="/manifest.webmanifest">'
    '<meta name="apple-mobile-web-app-capable" content="yes">'
    '<meta name="apple-mobile-web-app-status-bar-style" content="default">'
    '<meta name="apple-mobile-web-app-title" content="AlphaFest">'
)
PWA_REGISTRATION = (
    '<script id="af-pwa-install">'
    "if('serviceWorker' in navigator){window.addEventListener('load',function(){"
    "navigator.serviceWorker.register('/sw.js',{scope:'/'}).catch(function(){/* instalacao opcional */});"
    "});}"
    '</script>'
)


def inject_pwa(html: str) -> str:
    page = str(html or "")
    if not page or 'href="/manifest.webmanifest"' in page:
        return page
    if '</head>' in page:
        page = page.replace('</head>', PWA_HEAD_TAGS + '</head>', 1)
    if '</body>' in page:
        page = page.replace('</body>', PWA_REGISTRATION + '</body>', 1)
    return page


def pwa_assets() -> dict[str, bytes]:
    return {
        "manifest.webmanifest": json.dumps(MANIFEST, ensure_ascii=False, separators=(',', ':')).encode('utf-8'),
        "sw.js": SERVICE_WORKER.encode('utf-8'),
        "offline.html": OFFLINE_HTML.encode('utf-8'),
    }
