# 20.4.9-I8.13.5-HF24 — Continuidade dentro da Agenda Executiva do THU

Base funcional: **HF23 homologada**.

## Objetivo
Incorporar o sinal **THU • Sem avanço registrado** (HF21) à ordem única de decisão da **Agenda Executiva do Jorge**, sem remover o bloco detalhado de auditoria e sem criar qualquer automação de status.

## Mudanças
- A Agenda Executiva passa a receber, além de Retornos Comerciais, Cobranças Assistidas e prioridades de Produção/Entrega, os sinais de continuidade calculados a partir das fotografias diárias da Agenda da Anna.
- Pedido com sinal de continuidade aparece **uma única vez** na Agenda Executiva, mesmo quando também possui atraso, cobrança ou retorno comercial.
- Quando existe uma causa operacional mais concreta e urgente, ela continua como ação principal; **⏳ Sem avanço** aparece como contexto secundário.
- Um pedido que está no mesmo estágio por vários dias, mas ainda não possui outra prioridade operacional, pode entrar em **Resolver hoje** ou **Acompanhar**, conforme o nível calculado pela HF21.
- O bloco detalhado **⏳ THU • Sem avanço registrado** permanece abaixo da Agenda Executiva para conferência/auditoria.
- O mesmo conjunto de sinais é calculado uma única vez e reutilizado nos dois blocos, evitando divergência na mesma tela.
- O sinal continua significando somente **sem mudança de status registrada no Manager**; não afirma ausência de trabalho físico/offline.

## Segurança e compatibilidade
- Nenhum status, pagamento, produção, entrega, contato ou mensagem é alterado automaticamente.
- Sinal de continuidade nunca cria botão de WhatsApp nem registra contato.
- Se o módulo de continuidade não carregar, a Agenda Executiva continua funcionando com as demais fontes, preservando a resiliência da HF21.
- Anna permanece sem alteração nesta HF.
- `VERSAO` e `VERSAO.txt` foram alinhados em **20.4.9-I8.13.5-HF24**; na HF23 anexada, `VERSAO` ainda estava em HF21 apesar da interface usar HF23.
- Nenhum JSON/SQL operacional novo é criado.
