"""Teste da prévia: dados totalmente fictícios, sem integrações."""
from decimal import Decimal

from hf65_24_53_fictional_commercial_preview import (
    fictional_commercial_scenario, render_fictional_commercial_preview,
)


def test_preview_excludes_financial_exceptions_and_whatsapp_clicks():
    data = fictional_commercial_scenario()
    before, after = data["before"], data["after"]
    assert before["pedidos_pagos_atribuidos"] == 3
    assert before["receita_atribuida"] == Decimal("270.00")
    assert after["pedidos_pagos_atribuidos"] == 2
    assert after["receita_atribuida"] == Decimal("200.00")
    assert after["campanhas"] == [
        {"campanha": "instagram", "pedidos_pagos_atribuidos": 1,
         "receita_atribuida": Decimal("80.00")},
        {"campanha": "natal_2026", "pedidos_pagos_atribuidos": 1,
         "receita_atribuida": Decimal("120.00")},
    ]
    assert data["whatsapp_clicks_fictional"] == 42
    assert "NÃO comprova crédito bancário" in after["aviso"]


def test_preview_renders_only_demo_aggregates_without_network():
    class Area:
        def __init__(self):
            self.calls = []
        def metric(self, label, value):
            self.calls.append((label, value))
    class UI:
        def __init__(self):
            self.messages = []
            self.metrics = [Area(), Area(), Area()]
        def subheader(self, msg): self.messages.append(("subheader", msg))
        def warning(self, msg): self.messages.append(("warning", msg))
        def columns(self, count):
            assert count == 3
            return self.metrics
        def caption(self, msg): self.messages.append(("caption", msg))
        def dataframe(self, rows, **kw): self.messages.append(("table", rows))
        def info(self, msg): self.messages.append(("info", msg))
        def error(self, msg): self.messages.append(("error", msg))
    ui = UI()
    render_fictional_commercial_preview(ui)
    assert not any(kind == "error" for kind, _ in ui.messages)
    assert any(kind == "warning" and "FICTÍCIA" in msg for kind, msg in ui.messages)
    assert ui.metrics[1].calls[0][1] == 2
    assert ui.metrics[2].calls[0][1] == "R$ 200,00"
    assert all("EX-AT" not in str(item) for item in ui.messages)
