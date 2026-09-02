# AlphaFest Manager 20.4.9-I8.13.5-HF15

## THU • Cobranças Assistidas — fase inicial no Jorge

Base: **20.4.9-I8.13.5-HF14 homologada**.

### Objetivo

Dar continuidade ao ciclo de inteligência assistida do THU cobrindo a etapa imediatamente posterior à aprovação: pedidos aprovados com pagamento individual ainda pendente. A hotfix não automatiza cobrança, envio de mensagem ou confirmação de pagamento.

### Novo comportamento

- A Central do Jorge ganha **THU • Cobranças assistidas**.
- Entram na fila pedidos que estão:
  - Aprovado = SIM;
  - Pago = NÃO;
  - não encerrados;
  - fora do faturamento mensal.
- O THU prioriza:
  - pedido entregue e ainda não pago;
  - prazo de entrega vencido;
  - pedido Pronto aguardando pagamento;
  - entrega hoje/amanhã;
  - tempo desde a última cobrança registrada.
- **Cobrar** abre o WhatsApp com uma mensagem sugerida, sem envio automático.
- **Registrei cobrança** grava somente a referência temporal do contato financeiro e a trilha na proposta.
- Registrar cobrança **não marca Pago**.
- Quando o status Pago é confirmado pelo fluxo oficial, o pedido sai automaticamente da fila.
- Pedidos entregues e não pagos continuam na fila financeira: Entregue fecha a operação, não apaga uma pendência de recebimento.
- Clientes de faturamento mensal permanecem exclusivamente no fechamento mensal.
- A Central da Anna permanece sem esta nova interface durante a homologação.

### Metadados de acompanhamento

A proposta pode receber, somente após ação explícita do Jorge:

- `cobranca_registrada`;
- `primeira_cobranca_em`;
- `ultima_cobranca_em`;
- `cobranca_por`;
- `cobrancas_qtd`.

Esses campos são histórico de contato e nunca substituem `pago`/`pago_em`.

### Segurança

- Nenhuma mensagem é enviada automaticamente.
- Abrir o WhatsApp não conta como cobrança realizada.
- Nenhum status oficial é alterado pela fila do THU.
- `Pago` continua sendo a única fonte de confirmação financeira.
- Mensalistas não são tratados como cobrança individual.

### Homologação sugerida

1. No perfil Jorge, usar um pedido com **Aprovado = SIM** e **Pago = NÃO**.
2. Abrir a Central do Dia e confirmar o bloco **THU • Cobranças assistidas**.
3. Clicar em **Cobrar** e confirmar que o WhatsApp abre com a mensagem pronta, sem enviar.
4. Voltar ao Manager e clicar em **Registrei cobrança**.
5. Confirmar que o acompanhamento passa a indicar cobrança registrada hoje e que **Pago continua NÃO**.
6. Marcar Pago pelo fluxo oficial e confirmar que o pedido desaparece da fila de cobranças.

### Testes

- **81 testes automáticos aprovados**.
- Novos testes cobrem registro de cobrança, preservação do status Pago, exclusão de mensalistas/encerrados, pedido entregue não pago, pedido Pronto não pago, reinício do tempo após cobrança e remoção automática após pagamento.
