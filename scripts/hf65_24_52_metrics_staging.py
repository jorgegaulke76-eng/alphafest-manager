"""HF65.24.52: teste ponta a ponta da medição em Chromium sem Supabase real.

O servidor local representa exclusivamente a API REST de métricas. A página
é uma cópia de leitura do site público, com rastreador original REMOVIDO.
O script verdadeiro de métricas da branch é injetado com URL/key fictícias.
Toda rede fora do localhost é bloqueada e nenhum evento vai para produção.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from threading import Thread, Lock
import time
from unittest.mock import patch
from urllib.parse import quote, urlparse

from playwright.sync_api import sync_playwright

# Executado em 'scripts/', mas importa módulos puros da raiz do repositório.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import site_metrics_service as metrics
from hf65_24_52_browser_preview import (
    OUT, PRODUCT_NAME, PRODUCT_SLUG, build_public_preview,
)


def await_events(events: list[dict], lock: Lock, target: int, timeout: float = 8.0) -> list[dict]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with lock:
            snapshot = list(events)
        if len(snapshot) >= target:
            return snapshot
        time.sleep(0.05)
    raise AssertionError(
        f"Esperados {target} eventos no servidor de teste; recebidos {len(snapshot)}"
    )


def main() -> None:
    preview = build_public_preview()
    public_html = preview.read_text(encoding="utf-8")
    assert "alphafest-site-metrics" not in public_html
    assert 'id="hf52-preview-warning"' in public_html
    events: list[dict] = []
    blocked: list[str] = []
    lock = Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def do_GET(self):
            if self.path.startswith("/__af_geo"):
                data = b'{"city":"","region":"","country":""}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
            elif urlparse(self.path).path in ("/", "/novidades/"):
                data = staged_html
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
            else:
                self.send_response(404)
                data = b""
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            if urlparse(self.path).path != "/rest/v1/site_metrics_events":
                self.send_response(404)
                self.end_headers()
                return
            raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            data = json.loads(raw.decode("utf-8"))
            assert isinstance(data, dict)
            data["created_at"] = datetime.now(timezone.utc).isoformat()
            with lock:
                events.append(data)
            self.send_response(201)
            self.send_header("Content-Length", "0")
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_port
    origin = f"http://127.0.0.1:{port}"
    # Aponta o rastreador verdadeiro da branch APENAS para a API falsa local.
    mock_config = {"url": origin, "key": "sb_publishable_HF52_LOCAL_ONLY"}
    with patch.object(metrics, "tracking_available", return_value=True), patch.object(
        metrics, "public_config", return_value=mock_config
    ):
        staged_html = metrics.inject_tracking(public_html).encode("utf-8")
    assert b'id="alphafest-site-metrics"' in staged_html
    assert b"sb_publishable_HF52_LOCAL_ONLY" in staged_html

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            for device, width, height, mobile in [
                ("desktop", 1366, 850, False),
                ("celular", 390, 844, True),
            ]:
                # Testar sessões separadas, garantindo isolamento.
                with lock:
                    events.clear()
                blocked.clear()
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    is_mobile=mobile,
                    has_touch=mobile,
                    device_scale_factor=1,
                )

                def block_external(route):
                    request = route.request
                    if request.url.startswith(origin + "/"):
                        route.continue_()
                    else:
                        if request.method != "GET":
                            blocked.append(request.url)
                        route.abort()

                context.route("**/*", block_external)
                page = context.new_page()
                url = (
                    origin + "/?produto=" + quote(PRODUCT_SLUG)
                    + "&utm_source=instagram&utm_medium=stories"
                    + "&utm_campaign=hf52-staging-local"
                )
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.locator("#product-detail-modal").wait_for(state="visible")
                assert page.locator("#product-detail-name").inner_text() == PRODUCT_NAME
                before_click = await_events(events, lock, 2)
                counts = Counter(x["event_type"] for x in before_click)
                assert counts == {"page_view": 1, "product_open": 1}, counts
                for x in before_click:
                    assert x["utm_campaign"] == "hf52-staging-local"
                    assert x["utm_source"] == "instagram"
                    assert x["utm_medium"] == "stories"
                assert before_click[1]["product_name"] == PRODUCT_NAME
                assert before_click[1]["event_context"] == "campaign_product"

                # O clique acontece no elemento REAL. A tentativa de abrir o
                # WhatsApp é bloqueada pelo roteador de rede do teste.
                page.locator("#product-detail-whatsapp").click(timeout=10000)
                after_click = await_events(events, lock, 3)
                clicks = [x for x in after_click if x["event_type"] == "whatsapp_click"]
                assert len(clicks) == 1, after_click
                assert clicks[0]["product_name"] == PRODUCT_NAME
                assert clicks[0]["utm_campaign"] == "hf52-staging-local"
                assert clicks[0]["event_context"] == "site"

                # Nova página na mesma sessão; não há UTM na URL, mas o
                # rastreador deve recuperar a campanha sem atribuir nova venda.
                page.goto(origin + "/novidades/", wait_until="domcontentloaded", timeout=45000)
                diag = page.evaluate("""() => ({
                  url:location.href, ready:!!window.__alphafestMetricsReady,
                  storedUTM:sessionStorage.getItem('af_utm_v52'),
                  tracking:!!document.querySelector('#alphafest-site-metrics')
                })""")
                print(f"{device}: segunda página carregada: {diag}", flush=True)
                assert diag["ready"] and diag["tracking"], (
                    f"{device}: rastreador não foi inicializado na página seguinte: {diag}"
                )
                try:
                    final_events = await_events(events, lock, 4)
                except AssertionError:
                    with lock:
                        seen = [(x.get("event_type"), x.get("utm_campaign")) for x in events]
                    raise AssertionError(
                        f"{device}: não chegaram eventos da segunda página; "
                        f"estado={diag} eventos={seen}"
                    )
                fresh_pages = [x for x in final_events if x["event_type"] == "page_view"]
                assert len(fresh_pages) == 2, final_events
                assert fresh_pages[1]["utm_campaign"] == "hf52-staging-local"
                assert fresh_pages[1]["utm_source"] == "instagram"
                assert fresh_pages[1]["session_id"] == fresh_pages[0]["session_id"]

                # Usar a MESMA função do painel para validar a atribuição.
                now = datetime.now(timezone.utc)
                aggregated = metrics._campaign_opportunities(
                    final_events, now - timedelta(minutes=2), now + timedelta(minutes=2)
                )
                assert len(aggregated) == 1, aggregated
                campaign = aggregated[0]
                assert campaign["campanha"] == "hf52-staging-local"
                assert campaign["canal"] == "instagram"
                assert campaign["sessoes"] == 1
                assert campaign["sessoes_whatsapp"] == 1
                assert campaign["cliques_whatsapp"] == 1
                assert campaign["percentual"] == 100.0
                assert not blocked, f"{device}: POST externo bloqueado: {blocked}"

                # Relatório local só com dados agregados; não escrever IDs,
                # URLs com mensagens, cabeçalhos ou informações de cliente.
                report = {
                    "device": device,
                    "status": "aprovado",
                    "eventos": dict(Counter(x["event_type"] for x in final_events)),
                    "atribuicao": campaign,
                    "api": "LOCAL SIMULADA; SEM SUPABASE REAL",
                    "rede_externa_post": 0,
                }
                OUT.mkdir(exist_ok=True)
                (OUT / f"metricas-{device}.json").write_text(
                    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                print(f"{device}: eventos reais capturados LOCALMENTE e atribuídos: {report}", flush=True)
                context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
