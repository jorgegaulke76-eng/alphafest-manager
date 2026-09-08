# 20.4.9-I8.13.5-HF52.1-HF1 — Métricas quase em tempo real

## Objetivo
Atualizar o painel privado de métricas do site automaticamente, sem exigir F5 e sem aumentar desnecessariamente a carga no Supabase.

## Alterações
- atualização automática do bloco privado a cada 30 segundos;
- botão `↻ Atualizar agora` para leitura imediata sob demanda;
- indicador `Atualizado há Xs`, atualizado no navegador a cada segundo sem nova consulta ao banco;
- o rerun automático fica isolado no fragmento das métricas, sem recarregar o restante do Manager;
- nenhuma mudança no site público, na coleta de eventos ou nas políticas RLS;
- HF44 e todos os fluxos já homologados permanecem intactos.

## Banco
Nenhum SQL adicional é necessário. A tabela `site_metrics_events` criada no HF52.1 continua sendo usada.
