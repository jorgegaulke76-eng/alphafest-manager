# 20.4.9-I8.11.1-HF3 — Fonte Única de Status

## Objetivo
Eliminar divergências entre os status exibidos no perfil Jorge, Central da Anna,
THU, Alpha Core e painel de indicadores.

## Alterações
- Nova fonte única `proposal_status.py` para conclusão, encerramento, mensalista e pendência financeira individual.
- Mensalista: Aprovado + Entregue encerra a operação; pagamento segue exclusivamente para Faturamento Mensal.
- Clientes por proposta: Aprovado + Pago + Entregue continua sendo a regra de conclusão.
- Alpha Core e painel de indicadores passam a consumir a mesma regra oficial.
- Pagamento individual pendente exclui clientes mensalistas em todas as telas.
- Central da Anna, Central do Jorge e Histórico fazem leitura fresca do histórico nos pontos críticos.
- Atualização de status usa leitura fresca e compare-and-swap no Supabase quando disponível, com retry em conflito.
- Auditoria de status registra o usuário real que executou a alteração.
- Campos de pagamento de mensalistas ficam bloqueados nas telas operacionais; a baixa vem da Central de Faturamento Mensal.
- Diagnóstico de sincronização disponível no perfil Jorge para identificar casos que divergiriam pela regra antiga.

## Segurança de dados
- Nenhum banco JSON comercial foi migrado ou reescrito pela atualização.
- Nenhuma regra do Catálogo Oficial foi alterada.
- Nenhuma lógica de abatimento fixo ou faturamento mensal já homologada foi removida.
