# AlphaFest Manager 20.4.9-I8.13-HF1 — Datas reais + Histórico correto

## Objetivo
Corrigir a confiabilidade temporal da **Central de Entregas & Retiradas** sem alterar a arquitetura homologada da I8.13 e sem migrar/regravar dados operacionais.

## Pronto com data auditável
- Todo novo acionamento de **Pronto** grava `pronto_em` e `pronto_por` na proposta oficial.
- Quando **Entregue** implicar Pronto automaticamente, os mesmos metadados são registrados.
- Ao desmarcar Pronto antes da entrega, `pronto_em` e `pronto_por` são removidos juntos.
- Pedido legado sem `pronto_em` não recebe data inventada e aparece como **“Pronto · data de conclusão não registrada”**.
- O indicador **3+ dias** considera somente pedidos cuja data real de Pronto está registrada.

## Histórico de entregas
- Ordenação corrigida para usar **somente a data real da entrega** (`entregue_em` ou `data_entrega_real`).
- A data prevista (`data_entrega`) deixou de ser usada como fallback de ordenação.
- Entregas com data real aparecem da mais recente para a mais antiga.
- Registros legados sem data real permanecem no histórico, mas ficam no final e continuam identificados como **“data não registrada”**.

## Compatibilidade
- Nenhum banco novo.
- Nenhum JSON operacional migrado ou regravado pela atualização.
- A proposta oficial continua sendo a única fonte de Aprovado/Pago/Pronto/Entregue.
- A I8.13 permanece em homologação inicial no perfil Jorge.
