# AlphaFest Manager — HF53.3-HF8-HF39

## HF39 — Financeiro / faturamento mensal otimizado

O HF39 reduz cruzamentos repetidos entre Clientes, propostas e faturamento mensal sem alterar nenhuma regra financeira.

### Alterações
- cria índice leve de Clientes para o faturamento mensal, preservando exatamente a precedência histórica de relacionamento_id, WhatsApp, nome e documento;
- `montar_grupos_faturamento_mensal` carrega Clientes uma vez e deixa de varrer a base inteira para cada proposta mensal;
- perfis comerciais já resolvidos são reaproveitados dentro da mesma montagem de grupos;
- o Resumo mensal calcula a composição de faturamento em aberto uma única vez e a reutiliza no mês atual e no comparativo com o mês anterior;
- nenhuma baixa, cobrança, fechamento, recebimento, valor ou status é alterado automaticamente.

### Proteções
- resolução de clientes comparada por equivalência contra a rotina histórica em milhares de cenários;
- Template Mestre HF7 preservado;
- Template Anna preservado;
- Marketing Engine preservado.
