# 20.4.9-I8.11.1-HF2 — Fechamento Comercial + Reabertura Auditada

Base exclusiva: 20.4.9-I8.11.1-HF1.

## Escopo homologável — somente Jorge

- Corrige a exibição de **Pago no fechamento mensal** nas propostas vinculadas: o indicador agora reflete o pagamento propagado pela Central.
- Cada fechamento registrado ganha **observação comercial**, mensagem pronta para **WhatsApp**, **HTML** e **PDF** próprios.
- O documento do fechamento contém cliente, competência, vencimento, propostas incluídas, datas, valores, total, status e observações.
- Preparação do PDF é sob demanda para evitar custo em todo rerun do Streamlit.
- Fechamentos **Fechados, Faturados ou Recebidos** podem ser reabertos para correção.
- Reabertura exige motivo e registra usuário/data/hora em histórico auditável.
- Fechamento reaberto permanece vinculado às propostas para evitar duplicidade na composição mensal.
- No estado Reaberto, o Jorge pode corrigir propostas no Histórico, atualizar o fechamento pelos valores atuais e fechar novamente.
- Se já havia recebimento, ele é preservado. Após a correção, o sistema calcula **saldo adicional**, **crédito do cliente** ou **correção sem diferença financeira**.
- Recebimento anterior não é apagado silenciosamente e a data original de pagamento da proposta é preservada; ajustes recebem data própria.
- Fluxo normal continua: Fechado → Faturado → Recebido.
- Anna permanece sem acesso à Central de Faturamento Mensal até homologação no Jorge.

## Regras preservadas

- Faturamento mensal continua separado do pagamento por proposta.
- Somente propostas aprovadas + entregues entram no fechamento.
- O fechamento guarda referência/número e total negociado da proposta, sem duplicar preço de produto ou Catálogo Oficial.
- Perfil Comercial, abatimentos fixos, Catálogo Oficial, Inteligência e demais módulos homologados permanecem intactos.
