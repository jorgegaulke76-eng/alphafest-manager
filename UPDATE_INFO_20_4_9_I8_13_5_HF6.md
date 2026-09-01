# 20.4.9-I8.13.5-HF6 — Entregas, Retiradas e Logística modular

## Objetivo
Extrair do `app.py` as regras de logística e conclusão de saída sem alterar a Fonte Única de Status já homologada.

## Mudanças estruturais
- Novo `entregas_logistica_service.py`, sem dependência de Streamlit/Supabase.
- Formas de saída, observação logística e aviso ao cliente passam por uma única regra pura.
- Mensagem de pedido pronto para WhatsApp passa a usar o mesmo serviço.
- Antes de `Entregue = SIM`, a Central valida que a proposta continua oficialmente Pronta, ativa e ainda não Entregue.
- Persistência continua por leitura fresca da proposta; `Entregue` continua sendo gravado pela Fonte Única de Status e implica `Pronto`.
- Nenhum banco paralelo, nenhum SQL e nenhuma alteração automática de pagamento/estoque.

## Regra preservada
`Produção -> Pronto oficial -> Central de Entregas -> logística/aviso -> confirmar saída -> Entregue oficial`.

## Homologação sugerida
Usar um pedido realmente retirado/entregue: salvar logística, registrar aviso (quando aplicável), confirmar saída e marcar Entregue. Conferir que o pedido sai da fila aberta e permanece no Histórico recente de entregues.
