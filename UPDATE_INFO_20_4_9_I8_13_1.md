# 20.4.9-I8.13.1 — Inteligência de Prioridades e Atrasos

## Objetivo
Transformar prazo, status oficial, situação de produção/material e saída em uma prioridade operacional calculada automaticamente, sem criar um novo status e sem gravar prioridade manual na proposta.

## Regra central
- `Aprovado / Pago / Pronto / Entregue` continuam sendo os únicos marcos oficiais do pedido.
- Pedido `Pronto` nunca é tratado como atraso de produção.
- Se o prazo previsto de um pedido Pronto já passou, a atenção é classificada como `🚚 SAÍDA ATRASADA`.
- Prioridade é somente leitura e é recalculada a cada atualização da tela.

## Faixas calculadas
- `🚨 ATRASADO`: prazo vencido e produção ainda não concluída.
- `🔴 VENCE HOJE`: pedido ainda não Pronto com entrega hoje.
- `🔴 RISCO DE ATRASO`: leitura I8.12.7/I8.12.8 aponta risco de material/prazo.
- `🟠 PRÓXIMO DO PRAZO`: entrega em 1 ou 2 dias.
- `🟡 ATENÇÃO AO PRAZO`: entrega em 3 a 5 dias.
- `🟢 DENTRO DO PRAZO`: janela superior a 5 dias.
- `⚪ SEM DATA`: pedido aprovado aberto sem data de entrega.
- `🚚 SAÍDA ATRASADA`: pedido Pronto com data prevista já vencida.
- `📦 SAÍDA HOJE`: pedido Pronto previsto para sair hoje.
- `📱 CLIENTE NÃO AVISADO`: pedido Pronto sem registro de aviso.
- `⏳ PRONTO 3+ DIAS`: pedido Pronto aguardando saída por 3 dias ou mais, quando há data confiável de conclusão.
- `📦 AGUARDANDO SAÍDA`: produção concluída e saída sem urgência especial.

## Central Jorge
Nova leitura `🧠 Prioridades operacionais · I8.13.1` com indicadores de críticos, hoje, próximos 2 dias, Prontos para saída e pedidos sem data. O Top de atenção informa motivo e próxima ação e permite abrir o pedido.

A fila completa de produção passa a exibir a prioridade calculada de cada pedido sem alterar a etapa manual do Fluxo.

## Entregas & Retiradas
Pedidos Prontos recebem a mesma classificação de saída. Quando a data prevista venceu, a tela explica explicitamente que é atraso de retirada/entrega — não de produção.

## Persistência
Nenhum banco novo. Nenhum campo de prioridade é gravado. Os JSONs operacionais da base permanecem preservados.
