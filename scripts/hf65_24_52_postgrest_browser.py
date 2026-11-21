"""HF65.24.52: fluxo navegador -> rastreador real -> PostgREST real -> PostgreSQL.

Tudo opera em localhost e banco descartável do GitHub Actions, sem dados reais,
sem conexão com o Supabase/Cloudflare da AlphaFest e sem abrir o WhatsApp.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
from threading import Lock, Thread
import time
from unittest.mock import patch
from urllib.parse import urlparse

import requests
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import site_metrics_service as metrics
from site_carrinho_orcamento_service import inject_cart

PGRST = "http://127.0.0.1:3000/site_metrics_events"
NAME = "Bubble Personalizado de Teste"
HTML = (
    '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
    '<title>HF52 Teste Local</title></head><body>'
    '<article class="product-card" data-product="bubble-teste" '
    'data-detail-name="Bubble Personalizado de Teste"></article>'
    '<article class="product-card" data-product="caneca-teste" '
    'data-detail-name="Caneca Personalizada de Teste"></article>'
    '<div id="product-detail-modal">'
    '<span id="product-detail-name">Bubble Personalizado de Teste</span>'
    '<div class="product-detail-actions">'
    '<a id="cta" target="_blank" rel="noopener" '
    'href="https://wa.me/5511999999999?text=Quero%20um%20or%C3%A7amento">Solicitar orçamento</a>'
    '</div></div></body></html>'
)


def read_db() -> list[dict]:
    sql = """
        SELECT coalesce(json_agg(
          json_build_object(
            'event_type', event_type,
            'product_name', product_name,
            'page_path', page_path,
            'entry_path', entry_path,
            'referrer', referrer,
            'session_id', session_id,
            'utm_source', utm_source,
            'utm_medium', utm_medium,
            'utm_campaign', utm_campaign,
            'event_context', event_context,
            'created_at', created_at
          ) ORDER BY id
        ), '[]'::json)
        FROM public.site_metrics_events
        WHERE utm_campaign LIKE 'hf52-api-%';
    """
    result = subprocess.run(
        ["docker", "exec", "hf52-pg", "psql", "-X", "-A", "-t", "-U", "postgres",
         "-d", "postgres", "-c", sql],
        capture_output=True, text=True, check=True, timeout=20,
    )
    return json.loads(result.stdout.strip())


def wait_for_written_rows(target: int, *, timeout: float = 10) -> list[dict]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        rows = read_db()
        if len(rows) >= target:
            return rows
        time.sleep(0.15)
    raise AssertionError(
        f"PostgreSQL deveria conter {target} eventos, porém contém {len(read_db())}"
    )


def main() -> None:
    failed_http: list[int] = []
    blocked_external: list[str] = []
    lock = Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def do_GET(self):
            route = urlparse(self.path).path
            if route in ("/", "/novidades/"):
                data = injected_html
                mime = "text/html; charset=utf-8"
            elif route == "/__af_geo":
                data = b'{"city":"","region":"","country":""}'
                mime = "application/json"
            else:
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            if urlparse(self.path).path != "/rest/v1/site_metrics_events":
                self.send_response(404)
                self.end_headers()
                return
            raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            # O PostgREST usa o papel anon do banco temporário; somente
            # headers sem autenticação privilegiada são repassados.
            response = requests.post(
                PGRST,
                data=raw,
                headers={
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                timeout=15,
            )
            with lock:
                if response.status_code != 201:
                    failed_http.append(response.status_code)
            self.send_response(response.status_code)
            self.send_header("Content-Length", "0")
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    host = f"http://127.0.0.1:{server.server_port}"
    with patch.object(metrics, "tracking_available", return_value=True), patch.object(
        metrics, "public_config",
        return_value={"url": host, "key": "sb_publishable_HF52_TEST_ONLY"},
    ):
        # O carrinho da branch é injetado antes do rastreador, como no site real.
        with_cart = inject_cart(HTML, {"celular": "1199999999"})
        injected_html = metrics.inject_tracking(with_cart).encode("utf-8")

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            for index, (device, width, height, mobile) in enumerate(
                [("desktop", 1366, 850, False), ("celular", 390, 844, True)]
            ):
                campaign = f"hf52-api-{device}"
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    is_mobile=mobile,
                    has_touch=mobile,
                )

                def block_external(route):
                    if route.request.url.startswith(host + "/"):
                        route.continue_()
                    else:
                        # O clique do CTA pode tentar abrir wa.me em outra aba;
                        # o teste cancela a navegação antes de alcançar a rede.
                        if not route.request.url.startswith('https://wa.me/'):
                            blocked_external.append(route.request.method)
                        route.abort()

                context.route("**/*", block_external)
                page = context.new_page()
                page.goto(
                    f"{host}/?produto=bubble-teste&utm_source=instagram"
                    f"&utm_medium=stories&utm_campaign={campaign}"
                    "&telefone=11988887777#email=teste@example.org",
                    wait_until="domcontentloaded", timeout=30000,
                )
                page.wait_for_function("window.__alphafestMetricsReady === true")
                wait_for_written_rows(5 * index + 2)
                page.locator("#cta").click(timeout=7000)
                from urllib.parse import parse_qs
                href = page.locator("#cta").get_attribute("href") or ""
                message = parse_qs(urlparse(href).query).get("text", [""])[0]
                assert message.endswith(
                    "\n\nReferência da campanha: instagram/stories/" + campaign
                ), f"{device}: campanha não acompanhou a mensagem do WhatsApp"
                assert message.count("Referência da campanha:") == 1
                wait_for_written_rows(5 * index + 3)

                # A referência comercial precisa aparecer no carrinho com
                # vários produtos e permanecer editável antes do envio.
                page.locator("#afquote-add").click(timeout=7000)
                page.locator('#afquote-layer .afquote-close').click()
                page.locator("#product-detail-name").evaluate(
                    "(el) => { el.textContent = 'Caneca Personalizada de Teste'; }"
                )
                page.locator("#afquote-add").click(timeout=7000)
                page.locator("#afquote-review").click(timeout=7000)
                review = page.locator("#afquote-message")
                draft = review.input_value()
                expected_ref = (
                    "Referência da campanha: instagram/stories/" + campaign
                )
                assert "Bubble Personalizado de Teste" in draft
                assert "Caneca Personalizada de Teste" in draft
                assert draft.endswith(expected_ref), (device, draft[-180:])
                assert draft.count("Referência da campanha:") == 1
                # O cliente pode remover a origem no próprio WhatsApp.
                review.fill(draft.replace("\n\n" + expected_ref, ""))
                assert expected_ref not in review.input_value()
                # Recolocar para testar o texto final enviado por clique.
                review.fill(draft + "\nRevisão opcional de teste.")
                page.evaluate("""() => {
                  window.__hf52CartUrls = [];
                  window.open = (url) => {
                    window.__hf52CartUrls.push(url);
                    return {closed: false};
                  };
                }""")
                page.locator("#afquote-send").click(timeout=7000)
                urls = page.evaluate("window.__hf52CartUrls")
                assert len(urls) == 1, (device, urls)
                sent = requests.utils.unquote(urls[0])
                assert expected_ref in sent and "Revisão opcional de teste." in sent
                assert "Bubble Personalizado de Teste" in sent
                assert "Caneca Personalizada de Teste" in sent
                wait_for_written_rows(5 * index + 4)

                response = page.goto(
                    f"{host}/novidades/", wait_until="domcontentloaded", timeout=30000
                )
                assert response is not None and response.status == 200
                page.wait_for_function(
                    "window.__alphafestMetricsReady === true", timeout=10000
                )
                diag = page.evaluate("""() => ({
                  path:location.pathname,
                  utm:JSON.parse(sessionStorage.getItem('af_utm_v52')||'{}'),
                  tracker:!!document.querySelector('#alphafest-site-metrics')
                })""")
                print(f"{device}: segunda navegação e rastreador: {diag}", flush=True)
                assert diag["path"] == "/novidades/" and diag["tracker"]
                assert diag["utm"].get("campaign") == campaign
                rows = wait_for_written_rows(5 * index + 5)
                selected = [r for r in rows if r["utm_campaign"] == campaign]
                counts = Counter(r["event_type"] for r in selected)
                assert counts == {
                    "page_view": 2, "product_open": 1, "whatsapp_click": 2
                }, (device, counts)
                assert len({r["session_id"] for r in selected}) == 1
                assert all(r["utm_source"] == "instagram" and r["utm_medium"] == "stories"
                           for r in selected)
                assert all(r["page_path"] in ("/", "/novidades/") for r in selected)
                assert all("?" not in r["entry_path"] and "#" not in r["entry_path"]
                           for r in selected)
                assert not any(
                    term in json.dumps(selected, ensure_ascii=False)
                    for term in ["11988887777", "teste@example.org"]
                )

                now = datetime.now(timezone.utc)
                stats = metrics._campaign_opportunities(
                    selected, now - timedelta(minutes=5), now + timedelta(minutes=5)
                )
                assert len(stats) == 1 and stats[0]["sessoes"] == 1
                assert stats[0]["sessoes_whatsapp"] == 1
                assert stats[0]["cliques_whatsapp"] == 2
                assert sum(r["event_context"] == "carrinho" for r in selected) == 1
                print(
                    f"{device}: 5 eventos efetivamente persistidos em PostgreSQL local; "
                    "campanha atribuída e privacidade preservada",
                    flush=True,
                )
                context.close()
            browser.close()
        assert not failed_http, f"Falhas HTTP do PostgREST: {failed_http}"
        assert not blocked_external, (
            f"Tentativas inesperadas de conexão externa: {blocked_external}"
        )
        rows = read_db()
        assert len(rows) == 10, f"Total de linhas no banco local: {len(rows)}"
        print(
            "Integração real navegador -> PostgREST -> PostgreSQL: "
            "10 eventos em 2 dispositivos, zero conexões externas.",
            flush=True,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
