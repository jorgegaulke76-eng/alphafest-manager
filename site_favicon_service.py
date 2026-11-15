"""Ícones oficiais AlphaFest para o site estático (HF65.24.10)."""
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / 'assets' / 'site' / 'favicon'
FILES = {
    'favicon.ico': 'favicon.ico',
    'favicon.png': 'favicon-48.png',
    'favicon-16x16.png': 'favicon-16.png',
    'favicon-32x32.png': 'favicon-32.png',
    'apple-touch-icon.png': 'favicon-180.png',
    'android-chrome-192x192.png': 'favicon-192.png',
    'android-chrome-512x512.png': 'favicon-512.png',
}

FAVICON_TAGS = (
    '<link rel="icon" href="/favicon.ico" sizes="any">'
    '<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">'
    '<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">'
    '<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">'
)

def favicon_assets():
    return {name: (ASSETS / asset).read_bytes() for name, asset in FILES.items()}

def with_favicon(html):
    html = str(html or '')
    if 'href="/favicon.ico"' in html:
        return html
    return html.replace('</head>', FAVICON_TAGS + '</head>', 1)
