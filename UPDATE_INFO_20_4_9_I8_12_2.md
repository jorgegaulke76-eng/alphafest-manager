# 20.4.9-I8.12.2 — Estoque e Movimentação de Materiais

Base: 20.4.9-I8.12.1-HF1 homologada.

## Escopo
- Compras podem gerar entrada de estoque mediante opção explícita no lançamento.
- Cadastro de materiais de estoque com unidade e estoque mínimo.
- Saldo calculado por livro de movimentações; nenhuma movimentação histórica é apagada.
- Entradas manuais, saídas manuais, perdas e ajuste por contagem física.
- Bloqueio de saídas/estornos que deixariam saldo negativo.
- Estorno de movimentação preservando trilha de auditoria.
- Histórico das movimentações e alertas de estoque mínimo/zerado.
- Último custo de compra exibido por material quando houver correspondência de item/unidade.
- Exclusão de compra que lançou estoque estorna a entrada correspondente; se o estorno causaria saldo negativo, a exclusão é bloqueada.
- Restauração da compra pela Lixeira recria a entrada somente quando necessário.
- Backup geral passa a incluir estoque_db.

## Regra de segurança
Nesta etapa não existe baixa automática de estoque por proposta, venda ou entrega. Essa automação somente deverá ser criada após ficha técnica de consumo por produto ser homologada. O Catálogo Oficial e seus preços não são alterados automaticamente.
