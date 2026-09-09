# AlphaFest Manager 20.4.9-I8.13.5-HF16

## THU • Agenda Executiva — consolidação assistida no Jorge

Base: **20.4.9-I8.13.5-HF15 homologada**.

### Objetivo

Transformar os sinais que já existem no Manager em uma única ordem de ação para o Jorge, sem criar uma nova fonte de status e sem automatizar decisões. Retornos Comerciais, Cobranças Assistidas e prioridades de Produção/Entrega continuam existindo como filas específicas, mas a Agenda Executiva reúne o que merece ação em uma lista deduplicada por proposta.

### Novo comportamento

- A Central do Jorge ganha **THU • Agenda executiva** logo após a situação operacional.
- A agenda combina:
  - retornos comerciais com ação sugerida;
  - cobranças assistidas com ação sugerida;
  - pedidos operacionais atrasados, para hoje, próximos do prazo, Prontos/saída e sem data.
- A mesma proposta aparece **uma única vez** na agenda.
- Quando um pedido tem mais de uma pendência, a agenda mostra a mais urgente como ação principal e sinaliza as demais áreas que também exigem atenção.
- A ordem é dividida em **Fazer agora**, **Resolver hoje** e **Acompanhar**.
- Retorno/cobrança registrados hoje como “aguardar” não entram como tarefa executiva.
- Pedido operacional simplesmente dentro do prazo também não ocupa a agenda.
- Quando a ação principal é Comercial ou Financeira, a agenda oferece atalho para abrir o WhatsApp com mensagem pronta; nada é enviado automaticamente.
- O registro real de retorno/cobrança continua sendo feito somente nos blocos específicos. Abrir o WhatsApp pela agenda não conta como contato.
- O antigo **O que fazer agora** permanece para Anna; no Jorge ele é substituído pela nova agenda consolidada.

### Segurança

- Agenda somente leitura.
- Nenhum status Aprovado/Pago/Pronto/Entregue é alterado.
- Nenhum contato é registrado automaticamente.
- Nenhuma mensagem é enviada automaticamente.
- Nenhuma prioridade é persistida no banco.
- Os blocos homologados HF14/HF15 permanecem como trilha específica de ação e registro.

### Homologação sugerida

1. Entrar como **Jorge → Central do Dia**.
2. Confirmar o novo bloco **THU • Agenda executiva**.
3. Verificar se aparecem os pedidos mais urgentes organizados em Fazer agora / Resolver hoje / Acompanhar.
4. Se um mesmo pedido estiver atrasado e também com pagamento pendente, confirmar que ele aparece **uma única vez** na agenda e informa a segunda pendência em “Também exige atenção em”.
5. Se a ação principal for Retorno ou Cobrança, abrir o WhatsApp e confirmar que a mensagem fica preparada, sem envio automático e sem registrar contato.
6. Confirmar que Retornos Comerciais e Cobranças Assistidas continuam logo abaixo e funcionam como antes.

### Testes

- Testes específicos cobrem deduplicação entre áreas, exclusão de acompanhamento passivo, ordem por janela executiva, preservação do atalho de WhatsApp, ausência de dados inventados em ações internas, limite após ordenação e imutabilidade das filas de origem.
