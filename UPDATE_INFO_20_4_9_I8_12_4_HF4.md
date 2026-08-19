# AlphaFest Manager 20.4.9-I8.12.4-HF4 — Materiais Inativos / Históricos

## Objetivo
Fechar a higiene operacional do estoque após consolidações de materiais, preservando integralmente a rastreabilidade.

## Regras
- Materiais consolidados ficam marcados como **Inativo/Histórico**.
- Inativos não aparecem nas listas operacionais de novas compras, movimentações manuais ou Fichas Técnicas.
- O histórico de compras e movimentações anteriores permanece preservado.
- O material destino da consolidação continua como referência ativa oficial.
- Novo arquivamento manual só é permitido quando o material estiver com **saldo 0**, **sem pendências de pedidos** e **sem uso em Ficha Técnica**.
- Nenhum histórico é apagado.

## Interface
- Nova seção **Inativos / Históricos** no Estoque.
- Exibe motivo, eventual destino consolidado e data da inativação.
- Ação administrativa para arquivar cadastros antigos sem uso operacional com validações de segurança.

## Continuidade
Mantém todas as regras homologadas do HF3: Compras → Produto Oficial → Ficha Técnica → Material de Estoque → regularização automática das pendências.
