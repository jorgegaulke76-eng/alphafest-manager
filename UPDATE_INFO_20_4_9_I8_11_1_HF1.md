# 20.4.9-I8.11.1-HF1 — Hotfix da Central de Faturamento Mensal

## Correção
- Corrige `AttributeError` ao abrir a Central de Faturamento Mensal.
- O campo de busca de cliente agora usa uma normalização própria para texto simples.
- A função `normalizar_texto_busca`, destinada a dicionários de propostas, não é mais chamada com strings.
- Busca continua aceitando nome ou WhatsApp e passa a ignorar diferenças de maiúsculas/minúsculas e acentos.

## Escopo preservado
- Nenhuma regra financeira foi alterada.
- Ciclo Em aberto → Fechado → Faturado → Recebido preservado.
- Perfil Comercial, mensalistas e abatimentos fixos preservados.
- Primeira homologação da Central continua restrita ao perfil Jorge.
