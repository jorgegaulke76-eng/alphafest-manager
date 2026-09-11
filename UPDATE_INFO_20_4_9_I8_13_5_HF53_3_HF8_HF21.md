# AlphaFest Manager — HF53.3-HF8-HF21

## Objetivo
Reduzir consultas repetidas das métricas privadas do site sem alterar números, layout ou regras do painel.

## Entregas
- snapshot único paginado para page_view, product_open, whatsapp_click e search;
- contagens Hoje / 7 dias / 30 dias calculadas a partir do mesmo snapshot;
- eliminação das nove consultas extras de contagem em cada atualização;
- paginação automática acima de 5.000 eventos para manter precisão;
- cache curto de 25 segundos compartilhado com o Piloto Automático de Marketing;
- botão Atualizar agora limpa o cache e força nova consulta;
- HF7 e Template Anna preservados.
