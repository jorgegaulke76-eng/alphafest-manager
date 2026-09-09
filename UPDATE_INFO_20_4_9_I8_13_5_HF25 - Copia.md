# 20.4.9-I8.13.5-HF25 — THU • Prevenção de prazo e pressão de agenda

Base funcional: **HF24 homologada**.

## Objetivo
Fazer a Agenda Executiva do Jorge antecipar risco antes de o pedido entrar nas faixas críticas de atraso, sem criar uma capacidade produtiva fictícia e sem abrir um painel operacional paralelo.

## Mudanças
- Novo serviço somente leitura `thu_prevencao_prazo_service.py`.
- O radar considera pedidos aprovados, ativos, ainda não Prontos/Entregues, com entrega futura entre 3 e 10 dias.
- A leitura cruza:
  - data de entrega;
  - prazo de produção informado na proposta;
  - dias úteis restantes;
  - estágio atual da Central de Produção;
  - situação de material/liberação;
  - concentração de pedidos ainda não Prontos na mesma data.
- O sistema **não afirma capacidade exata**. Concentração de pedidos é tratada como `pressão de agenda`, um sinal qualitativo para organização.
- Pedidos com entrega em até 2 dias continuam pertencendo às Prioridades Operacionais existentes, evitando duplicar urgências já conhecidas.
- Sinal preventivo entra na Agenda Executiva com domínio `🛡️ Prevenção prazo`.
- Deduplicação preservada: se o mesmo pedido já possui atraso/entrega/cobrança/retorno/sem avanço, aparece uma única vez; urgência operacional concreta continua como causa principal.
- A própria Agenda Executiva ganha um expander `🛡️ Prevenção dos próximos 10 dias` para conferência dos sinais futuros mesmo quando a lista principal está ocupada por urgências atuais.
- Métrica `🛡️ Preventivos` adicionada à Agenda Executiva.

## Segurança e compatibilidade
- Nenhum status, mensagem, contato, pagamento, produção, entrega ou prioridade é gravado automaticamente.
- Nenhum banco/JSON/SQL novo é criado.
- Importação do radar é resiliente: falha do módulo não derruba o Manager.
- Compatibilidade com atualização parcial: se `app.py` novo subir antes do `thu_comercial_service.py` novo, a Agenda Executiva mantém o formato anterior em vez de falhar por assinatura incompatível.
- `VERSAO` e `VERSAO.txt` alinhados em **20.4.9-I8.13.5-HF25**.
