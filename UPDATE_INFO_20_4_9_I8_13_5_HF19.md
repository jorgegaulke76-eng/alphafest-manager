# 20.4.9-I8.13.5-HF19 — Fechamento Diário Comparativo da Anna

Base: **20.4.9-I8.13.5-HF18 homologada**.

## Objetivo
Transformar a Agenda diária da Anna em um ciclo real de abertura e fechamento do expediente, sem alterar pedidos automaticamente.

## Novo fluxo
- A Anna registra explicitamente a fotografia do **Início do dia**.
- A fotografia fica travada como referência daquele dia e é persistida no mesmo banco online (`app_data`), sem nova tabela ou SQL.
- O roteiro da manhã passa a ser baixado a partir dessa fotografia registrada, preservando a base de comparação.
- No fechamento, o Manager compara a situação atual com a abertura e separa:
  - **Entregues / concluídos** desde a manhã;
  - pedidos que **avançaram de status**;
  - pedidos/propostas que **entraram depois** da abertura;
  - pedidos que **seguem abertos** para o próximo período;
  - cancelamentos/encerramentos válidos, quando existirem.
- O fechamento possui PDF A4 paisagem, somente com dados e sem imagens.

## Segurança
- Registrar início do dia **não altera nenhuma proposta**.
- Gerar fechamento **não altera status**, contato, pagamento, produção ou entrega.
- A fotografia salva apenas os seis dados já exibidos na agenda: proposta, status, cliente, WhatsApp, produtos e entrega.
- Retenção limitada aos últimos 60 dias de fotografias para não crescer indefinidamente.
- Importação resiliente: se o módulo comparativo não carregar, a Agenda atual da Anna continua funcionando.

## Persistência
- Os 28 JSON/SQL já existentes da HF18 permanecem byte a byte iguais.
- É adicionado apenas `agenda_anna_snapshots_db.json`, documento temporário de apoio ao fechamento diário.
- Nenhuma tabela ou migração SQL nova.

## Validação técnica
- Suíte automatizada: **91 testes aprovados**.
- Todos os Python alterados compilados com sucesso.
- PDF comparativo testado com 1 e 2 páginas, cabeçalho repetido e sem imagens embutidas.
