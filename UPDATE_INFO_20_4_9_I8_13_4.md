# 20.4.9-I8.13.4 — Auditoria e Linha do Tempo Oficial

## Objetivo
Consolidar rastreabilidade operacional sem criar novos status e sem alterar o fluxo homologado.

## Principais mudanças
- Auditoria central agora usa append com compare-and-swap quando o Supabase está disponível, reduzindo risco de perda de eventos concorrentes.
- Alterações de Aprovado, Pago, Pronto e Entregue registram valor anterior e novo.
- Alterações logísticas e motivos de não fechamento passam a registrar mudanças oficiais.
- Observação operacional da Central do Dia deixa de salvar o histórico inteiro e passa a atualizar somente a proposta sobre leitura fresca do banco.
- Propostas do Jorge exibem uma "Linha do tempo oficial" com auditoria central e preservam os eventos históricos anteriores.
- Tela Núcleo Profissional → Auditoria exibe uma coluna de mudança (antes → depois).

## Segurança e custo
- Nenhum serviço novo.
- Nenhuma API paga.
- Nenhuma migração de dados necessária.
- Mantém o Supabase já protegido por credencial de servidor.
