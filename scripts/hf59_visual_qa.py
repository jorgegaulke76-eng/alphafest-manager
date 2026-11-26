"""QA real de navegador para página COMPLETA do site, com dados fictícios.

Não lê clientes nem acessa Supabase; não publica. Imagens de QA são SVGs
originais gerados aqui com o aviso DEPOIMENTO FICTÍCIO em destaque.
"""
from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

# Execucao direta por scripts/hf59_visual_qa.py precisa enxergar o projeto raiz.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright, expect
from site_completo_service import gerar_html_site_completo

OUT = Path("artifacts/hf59_visual").resolve()


def imagem_teste(n, largura, altura):
    cor = ("#dcefff", "#ffe7f1", "#e4f9ea", "#fff0d8")[n - 1]
    imagem = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{largura}" height="{altura}" '
        f'viewBox="0 0 {largura} {altura}"><rect width="{largura}" height="{altura}" fill="{cor}"/>'
        f'<rect x="12" y="12" width="{largura-24}" height="{altura-24}" rx="18" fill="white"/>'
        f'<text x="50%" y="27%" text-anchor="middle" font-size="23" fill="#13476c" '
        f'font-family="Arial" font-weight="bold">DEPOIMENTO FICTÍCIO</text>'
        f'<text x="50%" y="42%" text-anchor="middle" font-size="23" fill="#13476c" '
        f'font-family="Arial">TESTE VISUAL {n}</text>'
        f'<text x="50%" y="56%" text-anchor="middle" font-size="17" fill="#526a83" '
        f'font-family="Arial">SEM MENSAGEM REAL</text></svg>'
    )
    return "data:image/svg+xml;base64," + base64.b64encode(imagem.encode()).decode("ascii")


def escrever_site():
    OUT.mkdir(parents=True, exist_ok=True)
    dimensoes = [(440, 680), (640, 350), (430, 540), (520, 760)]
    depoimentos = [
        {
            "kind": "image", "active": True, "id": f"ficticio-{n}",
            "name": f"Pessoa fictícia {n}", "image_src": imagem_teste(n, *dims),
            "text": "Texto redundante de QA: NÃO DEVE APARECER NO CARTÃO.",
        }
        for n, dims in enumerate(dimensoes, 1)
    ]
    site = gerar_html_site_completo(
        [], {"nome": "AlphaFest - SOMENTE TESTE, NÃO PUBLICAR"},
        home_content_config={"testimonials": depoimentos},
        modo_preview=True,
        visual_hf48=True,
    )
    assert "hf6514-testimonial-zoom" in site, "Depoimentos não foram inseridos pelo gerador completo"
    assert site.count("O carinho dos nossos clientes") == 1
    assert "Texto redundante de QA" not in site
    path = OUT / "SITE_FICTICIO_PARA_REVISAO.html"
    path.write_text(site, encoding="utf-8")
    return path


def ensaio(browser, path, nome, largura, altura, mobile):
    ctx = browser.new_context(viewport={"width": largura, "height": altura},
                              is_mobile=mobile, has_touch=mobile, device_scale_factor=1)
    page = ctx.new_page()
    erros = []
    page.on("pageerror", lambda e: erros.append(str(e)))
    page.route("**/*", lambda route: route.abort() if route.request.url.startswith(("http://", "https://"))
               else route.continue_())
    page.goto(path.as_uri(), wait_until="domcontentloaded", timeout=25000)
    secao = page.locator("#depoimentos")
    expect(secao).to_be_visible(timeout=15000)
    botoes = secao.locator("button.hf6514-testimonial-zoom")
    assert botoes.count() == 4, f"{nome}: esperados quatro cartões de imagem"
    imagens = botoes.locator("img")
    for i in range(4):
        imagem = imagens.nth(i)
        imagem.scroll_into_view_if_needed()
        expect(imagem).to_have_js_property("complete", True, timeout=10000)
        assert imagem.evaluate("(e) => e.naturalWidth") > 0, f"{nome}: arte {i + 1} não carregada"
    secao.scroll_into_view_if_needed()
    secao.screenshot(path=str(OUT / (nome + "_galeria.png")), timeout=20000)
    primeiro = botoes.first
    primeiro.click()
    dialog = secao.locator("dialog.hf6514-testimonial-dialog")
    expect(dialog).to_be_visible()
    expect(dialog).to_have_attribute("open", "")
    ampliada = dialog.locator(".hf6514-testimonial-full")
    expect(ampliada).to_have_js_property("complete", True)
    assert ampliada.evaluate("(el) => el.naturalWidth") > 0
    assert ampliada.evaluate("(el) => el.currentSrc") == imagens.first.evaluate("(el) => el.currentSrc")
    dialog.screenshot(path=str(OUT / (nome + "_zoom.png")), timeout=20000)
    page.keyboard.press("Escape")
    expect(dialog).not_to_be_visible()
    page.wait_for_timeout(100)
    assert primeiro.evaluate("(el) => document.activeElement===el"), f"{nome}: foco não retornou"
    primeiro.click()
    dialog.locator(".hf6514-testimonial-close").click()
    expect(dialog).not_to_be_visible()
    box = secao.bounding_box()
    assert box is not None and box["width"] <= largura + 3, f"{nome}: seção excede largura"
    erros = [x for x in erros if "hf6514" in x.lower() or "testimonial" in x.lower()]
    assert not erros, f"{nome}: erro JavaScript da galeria: {erros}"
    ctx.close()
    return {"perfil": nome, "largura": largura, "altura": altura, "imagens": 4,
            "zoom": "aprovado", "escape": "aprovado", "fechar": "aprovado",
            "foco": "aprovado", "sem_rede_externa": True}


def main():
    assert not os.getenv("SUPABASE_SERVICE_KEY"), "Não é permitido usar secrets em QA"
    arquivo = escrever_site()
    with sync_playwright() as play:
        browser = play.chromium.launch(headless=True, args=["--no-sandbox"])
        resultados = [
            ensaio(browser, arquivo, "desktop", 1440, 900, False),
            ensaio(browser, arquivo, "celular", 390, 844, True),
        ]
        browser.close()
    report = {
        "status": "APROVADO", "origem": "site_completo_service.gerar_html_site_completo",
        "conteudo": "QUATRO IMAGENS FICTÍCIAS; NÃO SÃO DEPOIMENTOS REAIS",
        "publicado": False, "testes": resultados,
    }
    (OUT / "RELATORIO_VISUAL_HF59.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
