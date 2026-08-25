# 20.4.9-I8.13.2-CAT1-HF11

Correção de persistência dos status oficiais no perfil Jorge.

- remove gravação otimista por `on_change` do editor inline de status;
- adiciona botão explícito **Salvar status**;
- após salvar, relê a proposta com `force_refresh=True` e só confirma a baixa se Aprovado/Pago/Pronto/Entregue coincidirem com o banco;
- limpa o `session_state` dos widgets do pedido para impedir que um checkbox antigo reapareça como se fosse valor persistido;
- em falha, informa o erro e restaura a interface ao último valor realmente salvo;
- alertas de entregas passam a consultar `_status_resumo()` em vez do campo bruto `entregue`, mantendo compatibilidade com aliases legados.
