# 20.4.9-I8.11.2-HF2 — Unificação final de Atrasados

## Objetivo
Eliminar a última divergência observada entre THU, Alpha Core, Resumo Mensal e Central no indicador **Atrasados**.

## Correção
- O Alpha Core passou a expor uma única função de leitura: `listar_atrasados_operacionais`.
- THU deixa de recalcular atraso com regra própria e passa a consumir a lista oficial.
- Painel de indicadores/Resumo Mensal usa a mesma lista oficial.
- Central do Jorge usa a mesma lista para prioridade **O que fazer agora** e alertas de atraso.
- Propostas encerradas/canceladas não podem permanecer como atrasadas apenas por terem sido aprovadas no passado.
- Mensalistas operacionalmente concluídos permanecem fora da fila de atraso.

## Regra oficial
Um pedido está atrasado somente quando: proposta válida + operacionalmente ativa + aprovada + não entregue + data de entrega anterior à data atual.

## Escopo
Hotfix de leitura/indicadores. Nenhum banco comercial, proposta, produto, cliente ou fechamento é alterado. A Central da Anna não recebe mudança de interface.
