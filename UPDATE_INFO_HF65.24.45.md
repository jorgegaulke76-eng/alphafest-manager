# HF65.24.45 — Comunicação de Pedidos e Entregas

- Central de Pedidos: no pedido aberto, seção **Comunicar cliente · WhatsApp**.
- Modelos editáveis para aprovação da arte, pedido pronto e combinar retirada/entrega.
- Somente abre WhatsApp com texto pré-preenchido; o operador confirma manualmente o envio.
- Não registra aviso, não grava conteúdo da mensagem no banco, não altera status e não muda pagamento.
- Sem WhatsApp válido no pedido, oferece texto para cópia, sem direcionar a número incerto.
- Preserva área oficial de logística como Fonte Única para o registro do aviso.
- Nenhuma alteração no site Cloudflare, Secrets ou Supabase.

Testes: `python test_comunicacao_pedidos_hf45.py` e `python -m py_compile app.py comunicacao_pedidos_hf45.py`.
