# 20.4.9-C3 — Hotfix definitivo da busca

Base: 20.4.9-C2.

Correção:
- `unicodedata` é importado localmente dentro da função `_norm`;
- elimina o NameError observado no Streamlit;
- mantém integralmente a lógica de relevância da busca C1;
- nenhuma outra parte do sistema foi alterada.
