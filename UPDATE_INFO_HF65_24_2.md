# HF65.24.2 — Recuperação de inicialização e diagnóstico CAS

Base: ZIP **Arquivo atual.zip** enviado em 14/11/2026.

- Migrações durante o boot não interrompem mais toda a interface quando um CAS falha.
- A migração não avança a versão de dados após gravação não confirmada.
- Aviso de migração pendente permanece visível.
- CAS mostra HTTP status e código PostgREST (quando houver), mas não URLs, credenciais, resposta integral nem tokens.
- Não altera esquema do Supabase, Secrets, OAuth ou conteúdo de documentos.

**Atenção:** isto corrige o bloqueio da tela durante migração, não substitui a correção da causa remota da falha HTTP. Após instalar, conferir o código HTTP no aviso.
