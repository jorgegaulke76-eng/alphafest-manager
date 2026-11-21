"""Prévia isolada HF65.24.52 usando apenas o HTML público da vitrine AlphaFest.

- Baixa uma *cópia de leitura* do site atual.
- Substitui somente o script da ficha de produto pela implementação da branch.
- Remove o rastreamento Supabase da cópia e nunca grava no site ou no banco.
- Testa abertura real da ficha e registra capturas desktop/mobile via Playwright.

A prévia é um arquivo local, NÃO é uma publicação no Cloudflare.
"""
from __future__ import annotations

import ast
import html
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from site_metrics_dashboard_ui import published_products_from_html

OUT = ROOT / "hf52-preview-output"
SOURCE = "https://alphafest.com.br/"
PRODUCT_SLUG = "bubble-personalizado-com-confetes-e-baloes-metalizado"
PRODUCT_NAME = "Bubble Personalizado com Confetes e Balões Metalizado"


def product_script_from_branch() -> str:
    tree = ast.parse((ROOT / "site_vitrine_service.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "product_detail_script"
            for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise RuntimeError("Script da ficha de produto não localizado nesta versão")


def build_public_preview() -> Path:
    OUT.mkdir(exist_ok=True)
    req = Request(SOURCE, headers={"User-Agent": "AlphaFest-HF52-Preview/1.0"})
    with urlopen(req, timeout=25) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Site público não respondeu HTTP 200: {resp.status}")
        page = resp.read(48_000_001)
    if len(page) > 48_000_000:
        raise RuntimeError("HTML público maior que 48 MB: revisão manual necessária")
    print(f"HTML público obtido: {len(page) / (1024 * 1024):.1f} MiB")
    page = page.decode("utf-8")
    cards = re.findall(r'<article\s+class="product-card\b', page)
    if len(cards) != 92:
        raise RuntimeError(
            f"A prévia esperava 92 cards públicos, mas encontrou {len(cards)}. "
            "Revisar a versão publicada antes de homologar."
        )
    published = published_products_from_html(page)
    if len(published) != len(cards):
        raise RuntimeError(
            f"A seleção de produtos do Manager encontrou {len(published)} fichas "
            f"em vez das {len(cards)} publicadas. Verificar links duplicados."
        )
    if (PRODUCT_NAME, PRODUCT_SLUG) not in published:
        raise RuntimeError("Produto de referência não aparece na lista validada do Manager")
    print(f"Gerador de campanhas conferiu {len(published)} slugs da vitrine publicada", flush=True)

    # Remover exclusivamente o rastreador público que enviaria dados de navegação reais.
    page, metrics_count = re.subn(
        r'<script\b[^>]*\bid=["\']alphafest-site-metrics["\'][^>]*>[\s\S]*?</script>',
        "",
        page,
        flags=re.IGNORECASE,
    )
    if metrics_count != 1:
        raise RuntimeError(
            f"Era esperado exatamente 1 script de métricas; encontrados: {metrics_count}"
        )
    # O Worker público também injeta Cloudflare Web Analytics automaticamente.
    # Impedir que o HTML da prévia em arquivo gere beacon RUM (mesmo sem POST válido).
    page = re.sub(
        r'<script\b[^>]*src=["\']https://static\.cloudflareinsights\.com/beacon\.min\.js[^>]*></script>',
        "",
        page,
        flags=re.IGNORECASE,
    )
    old_detail = (
        r'<script>\s*\(function\(\)\{\s*'
        r"const modal=document\.getElementById\(['\"]product-detail-modal['\"]\);"
        r'[\s\S]*?</script>'
    )
    branch_detail = product_script_from_branch()
    # lambda impede que barras invertidas do JavaScript sejam interpretadas como
    # escapes do padrão de substituição por regex.
    page, script_count = re.subn(
        old_detail, lambda m: branch_detail, page, count=1, flags=re.IGNORECASE
    )
    if script_count != 1:
        raise RuntimeError(
            "Não foi possível substituir com segurança o script da ficha na cópia pública"
        )
    # O HTML público tem o CSS da versão 51; aplicar somente o trecho responsivo
    # da própria branch 52, nunca um CSS de teste divergente.
    vitrine_source = (ROOT / "site_vitrine_service.py").read_text(encoding="utf-8")
    css_start = vitrine_source.index(".product-detail-modal{{padding:8px;align-items:flex-end")
    css_end = vitrine_source.index(".product-detail-copy{{padding:0 2px}}", css_start)
    mobile_css = vitrine_source[css_start:css_end].replace("{{", "{").replace("}}", "}")
    page = page.replace(
        "</head>",
        '<style id="hf52-preview-mobile-css">@media(max-width:620px){'
        + mobile_css + "}</style></head>",
        1,
    )
    marker = (
        '<div id="hf52-preview-warning" style="position:fixed;top:0;left:0;right:0;'
        'z-index:2147483647;background:#fff4c7;color:#233b61;padding:6px 10px;'
        'font:700 12px/1.3 Arial;text-align:center">'
        'PRÉVIA ISOLADA HF65.24.52 — NÃO PUBLICADA • SEM RASTREAMENTO REAL</div>'
    )
    page = page.replace("<body>", "<body>" + marker, 1)
    output = OUT / "alphafest-hf65-24-52-previa.html"
    output.write_text(page, encoding="utf-8")
    print(f"Prévia pública isolada: {len(cards)} produtos; rastreador removido; ficha HF52 aplicada")
    return output


def test_in_real_browser(file_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    url = file_path.resolve().as_uri() + (
        "?produto=" + quote(PRODUCT_SLUG)
        + "&utm_source=instagram&utm_medium=stories&utm_campaign=hf52-homologacao"
    )
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for kind, width, height, mobile in (
            ("desktop", 1366, 850, False),
            ("celular", 390, 844, True),
        ):
            context = browser.new_context(
                viewport={"width": width, "height": height},
                is_mobile=mobile,
                has_touch=mobile,
                device_scale_factor=1,
            )
            # Nenhum POST externo pode sair da homologação.
            post_requests = []

            def safe_route(route):
                req = route.request
                if req.method != "GET":
                    post_requests.append(req.url)
                    route.abort()
                else:
                    route.continue_()

            context.route("**/*", safe_route)
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.locator("#product-detail-modal").wait_for(state="visible", timeout=10000)
            name = page.locator("#product-detail-name").inner_text().strip()
            assert name == PRODUCT_NAME, f"{kind}: produto errado: {name!r}"
            href = page.locator("#product-detail-whatsapp").get_attribute("href")
            assert href and href.startswith("https://wa.me/"), (
                f"{kind}: CTA WhatsApp não apontou para wa.me"
            )
            assert "alphafest-site-metrics" not in page.content(), (
                f"{kind}: prévia não deve conter rastreador real"
            )
            assert not post_requests, f"{kind}: houve tentativa POST: {post_requests}"
            rect = page.locator(".product-detail-panel").bounding_box()
            geometry = page.evaluate("""() => {
              const names=[\"#product-detail-modal\",\".product-detail-panel\",\".product-detail-close\",\".product-detail-media\"];
              return {innerWidth,innerHeight,scrollX,scrollY,
                docWidth:document.documentElement.scrollWidth,
                visual:window.visualViewport?{width:visualViewport.width,height:visualViewport.height,offsetLeft:visualViewport.offsetLeft,offsetTop:visualViewport.offsetTop,scale:visualViewport.scale}:null,
                boxes:names.map(q=>{const el=document.querySelector(q),r=el.getBoundingClientRect();return {q,x:r.x,y:r.y,w:r.width,h:r.height,position:getComputedStyle(el).position};})};
            }""")
            print(f"{kind}: dimensoes da prévia: {geometry}", flush=True)
            page.screenshot(path=str(OUT / f"previa-{kind}.png"), full_page=False)
            assert rect and rect["x"] >= -1 and rect["x"] + rect["width"] <= width + 1, (
                f"{kind}: ficha ultrapassa largura da tela: {rect!r} para {width}px"
            )
            print(f"{kind}: ficha aberta, dentro da tela, CTA preservado e sem POST")
            page.locator(".product-detail-close").click(timeout=5000)
            assert page.locator("#product-detail-modal").is_hidden(), (
                f"{kind}: ficha não fechou"
            )
            context.close()
        browser.close()


if __name__ == "__main__":
    html_path = build_public_preview()
    test_in_real_browser(html_path)
