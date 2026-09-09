# 20.4.9-I8.13.5-HF52.1-HF2 — Métricas por período + funil comercial

## Objetivo
Evoluir o painel privado de métricas do site sem alterar o site público, mostrando lado a lado o desempenho de Hoje, últimos 7 dias e últimos 30 dias, além de um funil comercial simples e mais confiável.

## Entregas
- painel privado preservado no Manager;
- atualização automática a cada 30 segundos preservada;
- botão `↻ Atualizar agora` preservado;
- três colunas de período: Hoje, Últimos 7 dias e Últimos 30 dias;
- cada período mostra Acessos, Produtos abertos e Cliques no WhatsApp;
- funil comercial de 30 dias calculado por sessão:
  - Acesso → Produto;
  - Acesso → WhatsApp;
  - Produto → WhatsApp;
- sessões e visitantes estimados continuam visíveis;
- rankings de produtos mais abertos e produtos que mais levaram ao WhatsApp preservados;
- `Hoje` considera o dia civil de São Paulo (`America/Sao_Paulo`).

## Segurança e compatibilidade
- nenhum SQL adicional é necessário;
- usa a mesma tabela `site_metrics_events` criada no HF52.1;
- a prévia interna continua fora da contagem;
- nenhuma alteração no site público, Catálogo, Galeria, publicação HF44 ou visual homologado.
