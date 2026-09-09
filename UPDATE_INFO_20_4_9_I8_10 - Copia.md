# 20.4.9-I8.10 — Inteligência Comercial dos Catálogos

## Objetivo
Transformar a Central de Catálogos em uma fila operacional comercial baseada somente em fatos registrados pelo AlphaFest Manager, sem inventar métricas de cliques ou visualizações.

## Entregas
- Nova aba **📊 Inteligência I8.10**, liberada para Jorge e Anna.
- Indicadores de catálogos ativos, publicados, sem publicação, vencidos, conteúdo alterado e saúde comercial.
- Fila inteligente priorizada para:
  - catálogo vencido;
  - conteúdo oficial alterado após a publicação;
  - referência ausente/inativa;
  - produto que deixou de ser elegível para a campanha;
  - catálogo nunca publicado;
  - catálogo próximo do vencimento.
- Histórico consolidado de publicações com responsável e validade.
- Contagem operacional de publicações por responsável.
- Visão de produtos mais presentes nos catálogos salvos, explicitamente sem tratar presença como clique, venda ou engajamento.

## Assinatura comercial sem snapshot
A partir da I8.10, cada nova publicação registra somente uma assinatura SHA-256 do conteúdo comercial efetivamente publicado. A assinatura é irreversível e não armazena preço, foto, descrição ou material antigos.

Quando o Catálogo Oficial muda, o Manager recalcula a assinatura atual e consegue recomendar republicação se ela não coincidir com a assinatura da última publicação.

Publicações anteriores à I8.10 continuam válidas normalmente, porém aparecem como **sem baseline** para comparação automática de alterações.

## Fonte única de verdade
O Catálogo Oficial continua sendo a única fonte de preço, foto, descrição, material, campanha e disponibilidade. A I8.10 não cria snapshots comerciais.
