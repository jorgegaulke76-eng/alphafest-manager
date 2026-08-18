# 20.4.9-I8.11.2-HF1 — Auditoria dos Indicadores Mensais e Diários

## Objetivo
Eliminar ambiguidades entre movimentações registradas no dia, situação operacional atual e conversão comercial do mês, preservando a Fonte Única de Status, o Radar HF4 e todas as regras já homologadas.

## Ajustes no perfil Jorge
- Conversão mensal passa a usar **aprovadas da coorte / todas as propostas emitidas na competência**.
- Propostas encerradas ou não fechadas continuam no denominador da conversão, pois representam oportunidades que não converteram.
- O expander do Resumo Mensal mostra a fórmula efetiva: aprovadas, emitidas, não convertidas e encerradas.
- O Resumo de hoje foi renomeado semanticamente para deixar claro que aprovações, entregas e recebimentos são **registros feitos hoje no Manager**.
- Adicionada auditoria que sinaliza aprovações registradas hoje de propostas emitidas anteriormente e entregas registradas hoje cuja previsão era anterior.
- A nova seção **Situação operacional agora** separa pedidos ativos, aprovação pendente, produção, prontos, atrasados e carteira aberta dos eventos registrados no dia.
- Agenda de hoje permanece informada separadamente com entregas ainda previstas e valor previsto.

## Segurança de interpretação
O Manager não retroage automaticamente uma atualização de status para uma data histórica que não esteja registrada. Quando a Anna regulariza hoje um status antigo, o sistema informa que se trata de um registro feito hoje e não afirma que o evento ocorreu hoje.

## Perfil Anna
A interface homologada da Anna permanece inalterada nesta versão. A auditoria e a nova disposição visual ficam restritas ao Jorge até homologação.
