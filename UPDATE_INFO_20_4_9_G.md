# 20.4.9-G — Auditoria e Fonte Única de Resultados

Base: 20.4.9-F aprovada.

- Central, Painel Executivo e Relatórios passam a compartilhar as mesmas regras para indicadores equivalentes.
- A Receber = propostas aprovadas, não pagas e não encerradas/canceladas.
- Recebido = propostas pagas e não encerradas/canceladas.
- Orçado hoje = propostas criadas hoje.
- Confirmado hoje = aprovações registradas hoje.
- Recebido hoje = pagamentos registrados hoje.
- Datas de eventos não são adivinhadas pelo campo genérico `atualizado_em`.
- Registros antigos sem data própria do evento são sinalizados na auditoria.
- Painel Executivo usa os mesmos indicadores operacionais da Central para Pedidos ativos, Atrasados, Em produção e Prontos.
- CRM, Central e Alpha Core usam a mesma regra para propostas encerradas/não fechadas.
- Histórico interpreta corretamente valores booleanos antigos.
- Relatórios ganhou a opção `Auditar números e resultados entre as telas`.
- A auditoria aponta duplicidades, estados incoerentes, ausência de data de evento e diferença entre total salvo e cálculo dos itens.
- “Produtos mais vendidos” foi corrigido para “Produtos mais orçados”, pois o ranking usa todas as propostas.

Nenhum histórico é apagado ou alterado automaticamente.
