# AlphaFest Manager — HF53.3-HF8-HF36

## HF36 — Snapshot operacional compartilhado

O HF36 reduz recomputações dentro da Central sem alterar nenhuma regra operacional.

- Previsão de produção, Central de Produção, fila de saídas e prioridades passam a ser calculadas uma única vez por rerun da Central.
- Agenda Executiva e blocos detalhados consomem a mesma fotografia operacional.
- Consumos, estoque e planejamentos são lidos uma vez e reaproveitados no mesmo ciclo.
- A fila de Entregas deixa de ser reconstruída novamente apenas para Prioridades.
- Mesmos status, riscos, prioridades, datas e regras já homologadas.
- Nenhuma gravação, automação de status ou mudança de fluxo foi criada.
- HF7, Template Anna e Marketing Engine permanecem preservados.
