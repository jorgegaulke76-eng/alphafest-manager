# AlphaFest Manager 20.4.9-I8.12.7 — Previsão de Produção e Risco de Entrega

## Objetivo
Transformar as fontes já homologadas de pedido, Ficha Técnica, estoque e planejamento de compras em uma visão operacional única de produção e prazo, sem criar uma segunda fonte de status.

## Fonte única
A I8.12.7 é calculada em tempo de leitura. Não existe novo banco de previsão.
Ela usa:
- propostas aprovadas ainda não entregues;
- consumo confirmado e pendências da I8.12.4;
- movimentações oficiais do estoque;
- solicitações/recebimentos do planejamento de compras I8.12.6;
- data de entrega já registrada na proposta.

## Classificações
- **🟢 Liberado para produção:** consumo confirmado e materiais totalmente atendidos.
- **🟠 Aguardando material:** existe falta real ainda sem cobertura suficiente de compra.
- **🛒 Compra em andamento:** toda a falta real do pedido está coberta por solicitação aberta ao fornecedor, mas ainda não foi recebida fisicamente.
- **⚪ Aguardando liberação de materiais:** proposta aprovada e não entregue, porém o consumo ainda não foi confirmado.
- **🔴 Risco de atraso:** tem precedência quando a entrega já venceu; quando a entrega é hoje/amanhã e ainda há material pendente; ou quando a previsão informada de recebimento ultrapassa a data de entrega.

## Proteção contra falsa cobertura
Quando vários pedidos aguardam o mesmo material, a quantidade aberta em compras é alocada em ordem FIFO de confirmação do consumo. Uma única solicitação ao fornecedor não pode aparecer como se cobrisse integralmente vários pedidos ao mesmo tempo.

## Limites desta etapa
A I8.12.7 **não estima tempo de fabricação** e não altera automaticamente a etapa manual de produção. O risco é material/prazo, baseado somente nas fontes objetivas disponíveis. Uma evolução futura poderá incorporar tempo técnico de produção se houver regra homologada por produto/processo.

## Comunicação entre telas
A mesma leitura é reutilizada em:
- Gestão → Compras, Custos & Estoque;
- Central do Jorge;
- Fluxo de Pedidos;
- Histórico/proposta;
- componente operacional compartilhado com Anna.

Nenhuma classificação movimenta estoque, cria compra, altera proposta ou modifica preço do Catálogo Oficial.
