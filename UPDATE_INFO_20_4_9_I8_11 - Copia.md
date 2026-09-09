# 20.4.9-I8.11 — Perfil Comercial do Cliente

## Objetivo
Criar a fundação comercial por cliente sem duplicar o Catálogo Oficial.

## Entregas
- Perfil Comercial dentro de Relacionamentos.
- Flag de **Faturamento mensal** com dia de fechamento, vencimento e observação.
- Propostas de mensalistas são identificadas automaticamente e não exigem marcação individual de `Pago`; o recebimento fica preparado para o fechamento mensal da I8.11.1.
- Filtros de Relacionamentos por mensalistas e clientes com abatimentos especiais.
- Abatimentos especiais **somente em valor absoluto (R$) por produto**, nunca em porcentagem.
- Fórmula oficial: `preço oficial atual - abatimento fixo = preço unitário aplicado na proposta`.
- O Catálogo Oficial não é alterado.
- A proposta salva o preço final efetivamente negociado naquele momento e não muda retroativamente.
- Cada regra registra produto, abatimento, validade opcional, motivo, usuário autorizador e data de atualização.
- Regras maiores que o preço oficial atual são bloqueadas no cadastro.
- Histórico mostra a modalidade de cobrança e mensalistas não geram falso alerta de “entregue e não pago”.
- Mensalistas saem do indicador normal `A receber`, ficando disponíveis como `mensais_a_faturar` para a próxima etapa.

## Próxima etapa planejada
20.4.9-I8.11.1 — Central de Faturamento Mensal: competência, fechamento, faturado, recebido e controle por cliente.
