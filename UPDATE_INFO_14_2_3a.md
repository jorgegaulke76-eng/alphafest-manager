# AlphaFest Manager 14.2.3a — Hotfix de inicialização

- Reduz o tempo máximo da primeira tentativa de conexão com o Supabase.
- Ativa um disjuntor de conexão: após uma falha, os documentos seguintes usam imediatamente a cópia JSON local.
- Mantém atendimento, orçamentos e digitação disponíveis durante instabilidades do banco online.
- Faz nova tentativa automática após o período de contingência.
- Não altera a Central da Anna nem estruturas de dados.
