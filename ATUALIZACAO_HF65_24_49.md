# HF65.24.49 — Planejamento diário da produção

- Resumo compacto de entregas atrasadas, hoje, amanhã e sem prazo.
- Busca por número, cliente e produto; abertura do pedido original.
- Orientação de combinar retirada/entrega se o pedido já está pronto.
- Reutiliza a fila carregada pela Central; nenhuma consulta extra ou gravação no banco.
- Status, financeiro, Agenda da Anna e catálogo preservados; sem estoque.
- Data prevista não é equivalente a horas de produção.
- Testes: `python -m pytest -q test_planejamento_diario_hf49.py test_planejamento_semanal_hf48.py`.
- Instalação: ZIP completo, extrair na pasta do repositório, GitHub Desktop commit + push; somente Manager.
