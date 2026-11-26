"""QA isolado da issue #8: largura móvel, navegação Mais e CTA WhatsApp.
Usa só quatro imagens fictícias; não conecta a banco, não publica.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

from hf59_visual_qa import escrever_site


def verificar(page, largura):
    page.goto(arquivo.as_uri(), wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(250)
    metrics = page.evaluate("""() => ({
      client: document.documentElement.clientWidth,
      scroll: document.documentElement.scrollWidth,
      more: (() => { const x=document.querySelector('.hf50-mobile-more>button'); return x ? x.getBoundingClientRect().toJSON() : null; })(),
      whatsapp: (() => { const x=document.querySelector('.mobile-whatsapp'); return x ? x.getBoundingClientRect().toJSON() : null; })()
    })""")
    assert metrics["scroll"] <= metrics["client"], (
        f"{largura}px: overflow horizontal: {metrics}"
    )
    for nome in ("more", "whatsapp"):
        b = metrics[nome]
        assert b, f"{largura}px: elemento {nome} não encontrado"
        assert b["left"] >= -1 and b["right"] <= largura + 1, (
            f"{largura}px: elemento {nome} fora da tela: {b}"
        )
    mais = page.locator(".hf50-mobile-more>button")
    mais.click()
    assert mais.get_attribute("aria-expanded") == "true", f"{largura}px: menu Mais não abre"
    menu = page.locator(".hf50-more-menu")
    assert menu.is_visible(), f"{largura}px: opções do menu não aparecem"
    page.keyboard.press("Escape")
    # O clique fora deve recolher o menu sem ocultar o CTA ou as opções.
    page.locator("body").click(position={"x": 2, "y": 350})
    assert mais.get_attribute("aria-expanded") == "false", f"{largura}px: menu Mais não fecha"
    return metrics


if __name__ == "__main__":
    arquivo = escrever_site()
    with sync_playwright() as engine:
        browser = engine.chromium.launch(headless=True, args=["--no-sandbox"])
        for width in (320, 390, 430):
            context = browser.new_context(viewport={"width": width, "height": 844},
                                          is_mobile=True, has_touch=True)
            page = context.new_page()
            page.route("**/*", lambda r: r.abort() if r.request.url.startswith(("http://", "https://")) else r.continue_())
            metrics = verificar(page, width)
            print(f"mobile {width}px: client={metrics['client']} scroll={metrics['scroll']} PASS")
            context.close()
        browser.close()
