# AlphaFest Manager 20.4.9-I8.12.8-HF1 — Fonte Única Operacional da Central

## Objetivo
Corrigir divergências percebidas entre os status atualizados por Anna/Jorge e as leituras das telas novas de Produção/Central, sem criar banco ou status paralelo.

## Regra arquitetural
Cada informação passa a ter um único dono:
- **Aprovado / Pago / Entregue:** proposta oficial (`historico_orcamentos`), pela fonte única `proposal_status.py`;
- **liberação, falta, compra e prazo:** motores homologados I8.12.4–I8.12.7;
- **etapa manual de produção:** `producao_db`, somente como andamento de trabalho.

O `producao_db` não decide se uma proposta está aprovada, paga, entregue ou encerrada.

## Correções
- Central e Fluxo usam a **mesma leitura fresca do Histórico** para sincronizar o espelho de produção e calcular previsão.
- Atualizações de Aprovado/Pago/Entregue reconciliam o Fluxo imediatamente após a confirmação no banco.
- `proposal_status.py` centraliza também a leitura dos aliases legados conhecidos (`Aprovado/aprovado`, `Pago/pago`, `Entregue/entregue`).
- Alpha Core, Painel de Indicadores, THU e I8.12.7 passam a consumir essa mesma leitura de status.
- Quando `Entregue` é marcado, o Fluxo preserva a etapa anterior. Se a entrega for desmarcada, a etapa é restaurada; registros antigos sem memória retornam para `Pronto`.
- A Central do Jorge deixa de considerar tarefas de propostas não aprovadas/entregues nos seus resumos operacionais.
- Pedidos em **Preparação / arte** ficam visíveis na fila prioritária e ganham contador próprio; assim um pedido com materiais liberados não “some” só porque ainda não está em `Pronto para produzir`.
- Etapas antigas como `Pronto` nunca superam bloqueios atuais de material/liberação.

## Auditoria visual
Foram adicionadas tabelas somente leitura no perfil Jorge mostrando, por pedido:
- Aprovado;
- Pago;
- Entregue;
- situação de materiais;
- etapa manual da produção.

Isso permite comparar a atualização feita pela Anna com a leitura da Central sem alterar nenhum dado.

## Compatibilidade
- Nenhum JSON novo.
- Nenhuma migração de dados.
- Histórico de produção preservado.
- Estoque, compras, consumo, fichas técnicas e planejamento não tiveram suas regras alteradas.

## Testes técnicos
- compilação de todos os arquivos Python;
- aliases legados de status pela fonte única;
- previsão I8.12.7 filtrando Aprovado/Entregue pela fonte oficial;
- Central: pronto para iniciar, preparação, bloqueio de material e etapa pronta antiga;
- entrega oficial + reabertura restaurando etapa anterior;
- Alpha Core e Painel de Indicadores usando a mesma leitura de status.
