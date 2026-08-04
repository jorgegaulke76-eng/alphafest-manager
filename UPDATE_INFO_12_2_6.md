# Versão 12.2.6 — THU oficial corrigido

- Inclui fisicamente o arquivo `assets/thu/thu_oficial.png`.
- Usa caminho absoluto baseado em `__file__`, compatível com Streamlit Cloud.
- Detecta automaticamente PNG/WebP e monta o MIME correto.
- Mantém fallback textual somente se o arquivo realmente não existir.
