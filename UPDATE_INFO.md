# AlphaFest Manager — HF53.3-HF8-HF38

## HF38 — Central: status e índices compartilhados

O HF38 otimiza Entregas, Prioridades e blocos operacionais da Central sem alterar a regra oficial Aprovado → Pago → Pronto → Entregue.

### Alterações
- a leitura oficial de status é calculada uma única vez por proposta no snapshot da Central;
- Entregas e Prioridades recebem o mesmo mapa oficial de status e deixam de recalculá-lo;
- listas de propostas operacionais, aprovadas abertas, aguardando aprovação e pagamentos pendentes são reaproveitadas do snapshot;
- índice por número da proposta é reutilizado nos alertas e nas rotinas de materiais;
- índice de consumos ativos é reutilizado em Pedidos em andamento;
- estoque e planejamentos já lidos no início da Central não são consultados novamente nesses blocos;
- nenhuma gravação automática, migração ou mudança de status.

### Proteções
- Fonte Única de Status preservada (`proposal_status.resumo_status`);
- Template Mestre HF7 preservado;
- Template Anna preservado;
- Marketing Engine preservado.
