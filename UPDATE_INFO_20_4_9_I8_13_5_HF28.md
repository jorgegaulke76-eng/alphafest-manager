# 20.4.9-I8.13.5-HF28 — Estorno visível de reserva/consumo por pedido

## Motivo
Na HF27 o motor auditado de estorno já existia, mas a interface de materiais reutilizava a fila de **liberação**, que por definição exclui pedidos com reserva/consumo ativo. Na prática, um pedido já reservado podia aparecer como “Materiais reservados” nas telas operacionais, mas não ficava selecionável para correção/estorno.

## Correção
- Novo bloco no perfil Jorge, em **Gestão → Compras, Custos & Estoque → Reserva de Estoque x Consumo Real**:
  - `↩️ Reservas/consumos ativos — corrigir ou estornar`;
  - seleção explícita do pedido com controle ativo;
  - detalhamento Necessário / Reservado / Consumido / Falta;
  - motivo obrigatório + confirmação auditada;
  - botão `↩️ Estornar liberação de materiais`.
- Reserva sem consumo físico: o estorno **somente libera a reserva**, sem alterar saldo físico.
- Pedido com consumo físico: a tela avisa antes e o fluxo próprio devolve apenas as baixas reais ativas vinculadas ao pedido, preservando histórico/auditoria.
- O estorno genérico de movimentação continua não sendo o caminho para consumo de pedido.

## Preservado
- HF27 — memória de tempo de ciclo observado permanece intacta.
- Reserva continua diferente de consumo físico.
- Nenhum status comercial/operacional é alterado automaticamente pelo estorno de materiais.
- Anna continua sem controles administrativos de estorno.
