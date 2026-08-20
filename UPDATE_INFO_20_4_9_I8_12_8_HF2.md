# AlphaFest Manager 20.4.9-I8.12.8-HF2 — Status Pronto + Resumo Operacional do Pedido

## Objetivo
Fechar a comunicação operacional entre proposta, produção, entrega e indicadores, acrescentando o status oficial **Pronto** sem criar uma fonte paralela.

## Fluxo oficial
**Aprovado → Pago → Pronto → Entregue**

- **Pronto**: produção concluída; pedido permanece operacionalmente aberto aguardando retirada do cliente ou entrega pela AlphaFest.
- **Entregue**: conclusão operacional. O pedido sai das filas abertas e permanece no Histórico.
- Marcar **Entregue** implica **Pronto** automaticamente.
- Desmarcar Entregue preserva Pronto; desmarcar Pronto, quando permitido, restaura a etapa manual anterior da produção.

## Fonte única
- Aprovado, Pago, Pronto e Entregue: proposta oficial.
- Material, falta, compra e risco: motores homologados I8.12.4–I8.12.7.
- `producao_db`: somente etapa manual de trabalho.
- Marcar o pedido pronto pela Central de Produção atualiza o Pronto oficial; o Pronto oficial também é refletido na etapa de produção de forma controlada.

## Indicadores e filas
- Pedidos Prontos não são tratados como produção atrasada.
- Pronto aparece separadamente como **aguardando retirada/entrega**.
- Pronto sai da fila de liberação de consumo, pois a produção já foi concluída.
- Entregue sai das filas operacionais e continua disponível no Histórico.
- Alpha Core, THU, Resumo Mensal, Central do Jorge, Fluxo, Previsão e Central de Produção usam a mesma leitura oficial.

## Resumo operacional dos produtos
Criada função única `resumo_produtos_pedido()` que lê exclusivamente os itens da proposta oficial e gera uma linha compacta, por exemplo:

`5× Caneca Porcelana · 30× Adesivo DTF · +2 itens`

O resumo foi propagado para listas e cards operacionais relevantes de Jorge e Anna, incluindo Central, Fluxo, Previsão, Produção, fila de liberação, Histórico, pesquisa e histórico do cliente.

## UX da Central
- O bloco curto foi renomeado para **Top prioridades de produção**.
- Foi acrescentada a **Fila completa de produção**, deixando explícito quando o pedido está contabilizado mas não faz parte do recorte urgente.
- Auditoria operacional exibe Aprovado, Pago, Pronto, Entregue, produtos, materiais e etapa manual na mesma linha.

## Compatibilidade e dados
- Nenhum banco operacional novo.
- Registros antigos Entregue sem campo `pronto` continuam sendo lidos como Pronto por compatibilidade.
- Os JSONs operacionais da base não são migrados nem regravados pela atualização.
