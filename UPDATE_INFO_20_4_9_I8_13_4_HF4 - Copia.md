# 20.4.9-I8.13.4-HF4 — Fila operacional com baixa oficial

## Correção
A Fila operacional da Central do Jorge ainda verificava `entregue` diretamente no registro bruto. Em propostas legadas, a Fonte Única de Status pode reconhecer a baixa por aliases/campos oficiais diferentes, fazendo um pedido já finalizado reaparecer como atrasado.

## Regra nova
- A Fila operacional passa a usar exclusivamente `proposal_status.resumo_status`.
- `Entregue` ou pedido encerrado/não fechado sai imediatamente da fila.
- Um registro antigo em `producao_db` não pode ressuscitar pedido já baixado.
- `Pronto` não é atraso de produção; aparece como aguardando retirada/entrega.
- Não aprovado é tratado como aprovação comercial pendente, não como atraso produtivo.
- A próxima ação da proposta também usa a mesma Fonte Única de Status.

Nenhuma migração de dados ou SQL é necessária.
