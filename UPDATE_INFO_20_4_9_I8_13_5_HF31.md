# 20.4.9-I8.13.5-HF31 — Qualidade da Base de Tempos

## Objetivo
Melhorar a leitura da memória de tempo de ciclo antes de qualquer cálculo quantitativo de capacidade.

## O que muda
- A memória continua preservando todas as amostras observadas.
- Com pelo menos 4 amostras do mesmo produto, durações estatisticamente muito distantes da mediana/MAD podem ser sinalizadas para conferência.
- Sinal de variação não apaga, corrige ou exclui automaticamente nenhum ciclo.
- Tabela passa a separar `Faixa central` (leitura auxiliar sem extremos sinalizados) de `Faixa total` (tudo que foi observado).
- Distribuição por lote/quantidade fica visível, evitando misturar silenciosamente referências de 1 unidade e lotes maiores.
- Bloco `Amostras com variação alta para conferir` mostra proposta, cliente, quantidade, início/fim e atalho para abrir o pedido.
- Nenhuma capacidade diária, prazo prometido ou tempo de mão de obra é calculado.

## Homologação sugerida
Na base atual do Papel de Arroz, a amostra de aproximadamente 20h47 deve permanecer na Faixa total, ser sinalizada para revisão e a Faixa central deve continuar próxima das amostras curtas, sem reduzir o total de ciclos observados.
