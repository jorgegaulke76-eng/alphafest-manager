# 20.4.9-I8.13.5-HF30 — Memória de ciclo alinhada à Fonte Única

## Objetivo
Corrigir o caso em que uma tarefa residual do Fluxo permanecia como `Em produção` na memória de tempos mesmo quando a proposta oficial já estava `Pronto` ou `Entregue`.

## O que muda
- A memória de ciclo passa a cruzar o espelho de produção com o Histórico oficial.
- `Pronto` ou `Entregue` na Fonte Única encerram a classificação de ciclo em andamento.
- Quando existe carimbo oficial confiável (`pronto_em` confiável ou `entregue_em`) posterior ao início, a HF30 deriva a amostra somente leitura e inclui o ciclo no resumo.
- Se o pedido está finalizado mas não possui horário final confiável, ele deixa de aparecer como em andamento, porém nenhuma duração é inventada.
- Nenhum status, estoque, reserva ou histórico de pedido é alterado pela memória.

## Homologação
No caso da proposta já entregue que aparecia como ciclo aberto, a Agenda Executiva deve deixar de mostrar `1 ciclo em andamento`. Havendo `entregue_em`/`pronto_em` confiável, o total de ciclos observados deve aumentar e a amostra entrar no produto correspondente.
