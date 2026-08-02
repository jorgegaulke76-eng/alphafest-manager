# FestManager 8.2.1 — Correção de inicialização

## Correção principal

- Corrige o `NameError: STATUS_FLUXO is not defined` que impedia o aplicativo de iniciar.
- Centraliza `STATUS_FLUXO` e `PRIORIDADES_FLUXO` no novo arquivo `constants.py`.
- Mantém o Alpha Creative Studio 8.2.0 e todos os dados existentes.
- Não altera clientes, propostas, catálogo, imagens, campanhas ou banco do Supabase.

## Instalação

Substitua os arquivos do pacote na raiz do repositório e reinicie o Streamlit.
