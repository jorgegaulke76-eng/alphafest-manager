# 20.4.9-I8.13.5-HF32 — Revisão Assistida dos Tempos

## Objetivo
Transformar variações detectadas pela HF31 em conhecimento operacional auditado, sem excluir ou corrigir amostras automaticamente.

## O que muda
- O bloco de variações permite registrar contexto real para cada amostra extrema.
- Opções: Pausa/espera, Retrabalho/ajuste, Máquina trabalhando sozinha, Status atualizado depois, Lote/quantidade atípica, Ciclo válido/duração real ou Outro contexto.
- Observação curta opcional pode complementar a classificação.
- A revisão é gravada no documento de auditoria já existente; não cria novo banco.
- Alterar a revisão cria novo evento auditado; a leitura usa a revisão mais recente e preserva as anteriores no histórico.
- A duração original, mediana, faixa total e número de ciclos nunca são reescritos pela revisão.
- A faixa central continua sendo apenas leitura auxiliar sem extremos estatísticos.
- Nenhuma capacidade diária ou promessa de prazo é calculada.

## Homologação sugerida
Na variação longa do PAPEL DE ARROZ, registrar o contexto que corresponda ao ocorrido. Após salvar, o contador deve passar de 1 pendente / 0 revisada para 0 pendente / 1 revisada, mantendo 4 ciclos observados, mediana 34 min, faixa central 30–37 min e faixa total 30 min–20h47.
