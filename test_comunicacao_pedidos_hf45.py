from comunicacao_pedidos_hf45 import MODELOS, mensagem_modelo, numero_whatsapp, url_whatsapp
from urllib.parse import unquote


def test_templates():
    for k in MODELOS:
        m = mensagem_modelo(k, "PED-42", "Ana")
        assert "PED-42" in m and "Ana" in m
        assert "R$" not in m


def test_whatsapp():
    assert numero_whatsapp("(11) 99999-1234") == "5511999991234"
    assert numero_whatsapp("5511999991234") == "5511999991234"
    assert not numero_whatsapp("123")
    assert not url_whatsapp("123", "Oi")
    assert unquote(url_whatsapp("11999991234", "Olá!")) == "https://wa.me/5511999991234?text=Olá!"


if __name__ == "__main__":
    test_templates()
    test_whatsapp()
    print("HF45 OK")
