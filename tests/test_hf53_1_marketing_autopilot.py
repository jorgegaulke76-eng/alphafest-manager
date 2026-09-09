from pathlib import Path

from alpha_marketing_autopilot import rank_products


def test_rank_products_requires_image_and_prefers_whatsapp_signal():
    catalog = [
        {"Nome": "Caneca A", "Imagens": ["a.png"], "Descricao": "desc", "Categoria": "Brindes"},
        {"Nome": "Topo B", "Imagens": ["b.png"], "Descricao": "desc", "Categoria": "Festas"},
        {"Nome": "Sem Foto", "Imagens": [], "Descricao": "desc"},
    ]
    metrics = {
        "top_products": [{"product_name": "Caneca A", "count": 2}],
        "top_whatsapp_products": [{"product_name": "Topo B", "count": 5}],
    }
    ranked = rank_products(catalog, metrics, 10)
    assert [x["name"] for x in ranked][0] == "Topo B"
    assert "Sem Foto" not in [x["name"] for x in ranked]


def test_hf53_1_ui_contract_present():
    app = Path("app.py").read_text(encoding="utf-8")
    assert "Piloto Automático de Conteúdo" in app
    assert "Gerar campanha automaticamente" in app
    assert "Aguardando aprovação" in app
    assert Path("VERSAO.txt").read_text(encoding="utf-8").strip() == "20.4.9-I8.13.5-HF53.3-HF8-HF1"
