# 20.4.9-I8.13.3-HF1

Hotfix de compatibilidade com as novas Secret Keys do Supabase (`sb_secret_...`).

- Corrige `cloud_db._headers()` para enviar chaves novas apenas no cabeçalho `apikey`.
- Mantém `Authorization: Bearer` somente para chaves legadas JWT (`anon`/`service_role`).
- Evita HTTP 401 / Invalid JWT após o hardening que remove o acesso `anon` à tabela `app_data`.
- Não altera dados operacionais, regras comerciais, estoque, catálogo ou propostas.
