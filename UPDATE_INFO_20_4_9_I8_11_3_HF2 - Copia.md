# 20.4.9-I8.11.3-HF2 — Ações rápidas do Jorge + formatação monetária

Base: 20.4.9-I8.11.3-HF1 fornecida pelo usuário.

## Correções
- Restaura `📋 Duplicar pedido` e `🗑️ Excluir proposta` no painel rápido/alerta de proposta do perfil Jorge.
- Mantém a exclusão bloqueada para o perfil Anna, inclusive na função administrativa.
- A exclusão continua enviando a proposta para a Lixeira.
- Corrige definitivamente a linha `Quantidade × Valor Unitário = Total` na digitação/edição, evitando que `R$` seja interpretado como expressão matemática pelo Markdown do Streamlit.
- Preserva Evento, prévia em tempo real, preços especiais, WhatsApp, HTML/PDF, Radar e indicadores homologados.
