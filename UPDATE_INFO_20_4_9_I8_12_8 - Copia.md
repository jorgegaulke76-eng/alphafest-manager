# AlphaFest Manager 20.4.9-I8.12.8 — Central de Produção

## Objetivo
Transformar a previsão homologada da I8.12.7 em uma fila operacional de produção sem criar uma nova fonte de status.

## Fonte única
- pedido: Histórico de propostas;
- materiais/prazo: motor I8.12.7;
- etapa manual: `producao_db.json`, o mesmo Fluxo de Pedidos já existente.

Nenhum novo banco foi criado.

## Central de Produção
No Fluxo de Pedidos, Jorge e Anna passam a enxergar uma fila única dos pedidos aprovados e ainda não entregues com:
- risco/prazo;
- situação de materiais;
- etapa manual da produção;
- próxima ação operacional;
- prioridade e data de entrega.

## Ações rápidas seguras
- **Iniciar produção** somente quando materiais estiverem liberados e todos os itens estiverem em etapa compatível;
- **Marcar pedido pronto** somente quando todos os itens estiverem em produção ou já prontos.

As ações atualizam o `producao_db` existente, registram timeline e atividade. Elas não alteram estoque, preços ou compras.

## Comunicação
- Central do Jorge recebe resumo da fila operacional;
- Fluxo de Pedidos é a central de ação compartilhada;
- o componente de pedido usado em Histórico/Fluxo mostra também a etapa manual de produção junto da previsão I8.12.7.

## Regras preservadas
- nenhum status derivado paralelo é persistido;
- risco não impede iniciar produção se materiais e etapa permitirem;
- material pendente ou consumo ainda não liberado bloqueiam a ação rápida de iniciar;
- entrega continua sendo registrada pelo fluxo/status já existente.
