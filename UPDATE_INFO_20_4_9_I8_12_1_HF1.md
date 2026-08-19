# 20.4.9-I8.12.1-HF1 — Correção visual dos alertas de custo

Hotfix restrito à apresentação do módulo **Compras & Custos**.

- Corrige a interpretação indevida do caractere `$` pelo Markdown/LaTeX do Streamlit nos alertas de comparação de custo.
- Alertas passam a exibir valores monetários no formato esperado, por exemplo: `R$ 0,20` e `R$ 1,60`.
- Remove os asteriscos visíveis que apareciam em alguns avisos.
- Mantém intactas as regras de comparação, histórico, fornecedores, Catálogo Oficial e preços de venda.
- Nenhum JSON comercial é migrado ou alterado por este hotfix.
