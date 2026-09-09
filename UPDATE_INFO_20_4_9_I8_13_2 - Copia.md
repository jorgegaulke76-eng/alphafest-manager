# 20.4.9-I8.13.2 — Reserva de Estoque x Consumo Real

## Objetivo
Separar material comprometido com pedidos de material fisicamente consumido na produção, sem criar um segundo estoque e sem alterar os marcos oficiais Aprovado/Pago/Pronto/Entregue.

## Regra operacional
- A aprovação continua colocando o pedido na fila de liberação de materiais.
- A liberação humana existente foi preservada como trava de segurança: ao confirmar, o Manager registra a necessidade e RESERVA o saldo livre; não baixa o físico.
- `Saldo livre = saldo físico − reservas ativas`.
- Se não houver saldo livre suficiente, somente a diferença fica como falta real para Compras.
- Entradas de estoque completam reservas pendentes automaticamente em FIFO.
- Ao iniciar efetivamente a produção, a reserva é convertida em consumo físico e o estoque é baixado.
- Marcar Pronto/Entregue por um caminho novo também garante o consumo físico antes de concluir a produção; pedidos legados que já estavam Prontos não recebem exigência retroativa.
- Estornar antes da produção apenas libera a reserva. Estornar depois do consumo devolve as baixas físicas ativas e libera o controle do pedido.

## Proteções
- Saída manual não pode usar quantidade já reservada para pedidos.
- Perda ou ajuste de inventário pode refletir a realidade física; se o saldo ficar abaixo do reservado, o Manager reduz primeiro as reservas mais novas e devolve os pedidos afetados para falta de material.
- Consolidação de material é bloqueada enquanto houver reserva ativa no material de origem.
- Dados legados da I8.12.4 com baixas já realizadas são reconhecidos como consumo real e não recebem baixa duplicada.

## Interface
Estoque passa a mostrar separadamente:
- Saldo físico;
- Reservado;
- Disponível livre;
- Falta em pedidos.

A prévia do pedido mostra quanto pode ser reservado agora. O detalhamento do pedido mostra Necessário / Reservado / Consumido / Falta. Simulador e capacidade de Ficha Técnica passam a usar o saldo livre, não o material comprometido com outros pedidos.

## Arquitetura
- Nenhum banco novo.
- Reservas ficam no mesmo `consumo_pedidos_db` que já registra a necessidade do pedido.
- `estoque_db` continua sendo a única fonte de movimentação física.
- Compras e Previsão continuam usando `pendente`, agora definido como a falta NÃO coberta por consumo nem reserva.
