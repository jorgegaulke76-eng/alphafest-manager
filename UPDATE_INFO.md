# HF65.19 — Recibo de Pagamento

- Gera recibo somente para proposta/pedido com status oficial **Pago**.
- **🧾 Enviar recibo** abre o WhatsApp do cliente com mensagem pronta.
- **📄 Recibo HTML** gera documento A4 para imprimir ou salvar em PDF.
- Usa cliente, CPF/CNPJ quando informado, número da proposta, itens, valor oficial e data `pago_em`.
- Número do recibo: `REC-<número da proposta>`.
- Disponível na Central da Anna, Central do Jorge e Histórico.
- Clientes de fechamento periódico continuam com o documento próprio do fechamento, evitando duplicidade.
- Sem alteração de schema e sem dados persistentes no pacote.
