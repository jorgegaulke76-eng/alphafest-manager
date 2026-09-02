# AlphaFest Manager 20.4.9-I8.13.5-HF17

## Agenda Operacional da Anna

Esta hotfix adiciona à Central Operacional da Anna um roteiro diário imprimível com todas as propostas e pedidos ainda abertos.

### Dados exibidos
- Número da proposta
- Status resumido atual
- Nome do cliente
- WhatsApp
- Produto(s) e quantidade(s)
- Data de entrega

Nenhuma imagem, foto, vídeo ou prévia do Catálogo é incluída.

### Impressão
A Central oferece dois PDFs A4 paisagem:
1. **Início do dia** — fotografia das pendências no começo do trabalho.
2. **Fechamento do dia** — nova fotografia das pendências no fim do expediente.

Os arquivos registram data e hora da geração e são ordenados pela data de entrega mais urgente.

### Segurança operacional
A agenda é somente leitura. Ela não muda status, não registra contato, não envia WhatsApp e não grava nenhuma informação nova na proposta.

A importação do módulo é resiliente: caso uma atualização parcial deixe o arquivo da agenda indisponível, a Central da Anna continua abrindo normalmente.

### Validação técnica
- Suíte automatizada ampliada para 94 testes.
- PDF de 24 linhas validado em 2 páginas, com cabeçalho repetido e sem imagens embutidas.
- 28 arquivos JSON/SQL preservados sem alteração em relação à HF16.
