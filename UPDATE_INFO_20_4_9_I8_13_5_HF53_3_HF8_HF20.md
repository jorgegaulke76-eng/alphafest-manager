# AlphaFest Manager — HF20

## Otimização de reruns
- Backups manuais da barra lateral passam a ser serializados somente quando solicitados.
- Alertas de entrega/produção são calculados apenas nas telas que realmente os exibem.
- A leitura de Atendimentos da barra lateral é reutilizada no badge do mesmo rerun.
- AlphaFest Live e Radar compartilham snapshot de leitura por 10 segundos, reduzindo consulta duplicada sem afetar gravações.
- Regras de negócio, HF7 e Template Anna não foram alterados.
