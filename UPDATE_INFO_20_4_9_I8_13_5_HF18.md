# 20.4.9-I8.13.5-HF18 — Agenda da Anna e Histórico na mesma Fonte Única

- Corrige divergência entre a Agenda diária da Anna e os alertas do Histórico.
- Agenda, Histórico e operação passam a considerar o mesmo universo de proposta aberta: registro não cancelado/encerrado de forma válida e ainda não Entregue.
- Marcas comerciais antigas de “não fechado” deixam de esconder pedidos que depois avançaram para Pago, Pronto ou Entregue; cancelamentos/arquivamentos explícitos continuam encerrados.
- Ao salvar um avanço real de status, marcas antigas de “não fechado” são limpas para evitar nova divergência.
- Status da Agenda deixa de inferir “Em produção” apenas porque o pedido foi aprovado: passa a mostrar os marcos reais (Aprovado, Pago, Pronto, aguardando retirada/entrega).
- Prazo vencido é separado em produção atrasada, saída atrasada e proposta ainda aguardando aprovação.
- Pedidos pagos com entrega futura permanecem visíveis na Agenda sem serem classificados como atrasados.
- Nenhum JSON, SQL ou banco operacional foi alterado.
