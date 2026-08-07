# AlphaFest Manager 20.3.5

## Hotfix da tela Atenção

- Corrige instabilidade visual `NotFoundError: removeChild` no frontend do Streamlit.
- Remove `st.rerun()` imediato dos botões de alerta e usa callbacks nativos do Streamlit.
- Cada alerta passa a ter container próprio e árvore visual estável.
- Mantém intacta a correção 20.3.4 das fotos persistentes do catálogo.
- Não altera banco, propostas, catálogo, Marketing Studio ou templates.
