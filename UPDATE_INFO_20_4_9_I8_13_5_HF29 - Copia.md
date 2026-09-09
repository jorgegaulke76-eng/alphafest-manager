# 20.4.9-I8.13.5-HF29 — THU • Identificação do ciclo em andamento

## Objetivo
Eliminar a caixa-preta da memória de tempo de ciclo: quando houver ciclo observado em andamento, o Jorge precisa saber exatamente qual pedido está sendo medido antes de homologar a coleta.

## O que muda
- O bloco `⏱️ Memória de tempos de produção` passa a listar cada ciclo em andamento com:
  - proposta;
  - cliente;
  - produto;
  - quantidade;
  - horário explícito de início;
  - usuário que iniciou, quando disponível;
  - botão `📋 Abrir pedido`.
- O contador continua somente leitura e não altera nenhum status.
- Pedidos sem início confiável continuam separados; nenhum horário retroativo é inventado.

## Continuidade
- HF28 — estorno auditado de reservas/consumos permanece intacto.
- HF27 — coleta e resumo de tempos de ciclo permanecem com a mesma regra; a HF29 apenas torna o ciclo aberto identificável.

## Homologação
Abrir a Agenda Executiva do Jorge e conferir se o item mostrado em `Ciclo(s) em andamento` corresponde ao pedido que deverá ser finalizado. Depois, ao marcar esse mesmo pedido como Pronto pelo fluxo oficial, confirmar que o contador em andamento cai e a amostra observada aumenta quando houver ciclo válido.
