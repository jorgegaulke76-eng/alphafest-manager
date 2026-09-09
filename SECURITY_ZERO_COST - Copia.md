# AlphaFest Manager — segurança custo zero (I8.13.3)

Esta versão prepara o Manager para fechar a escrita anônima do Supabase sem contratar nenhum serviço.

## O que já foi aplicado no código

- Gravações online só atualizam o cache da sessão depois que o banco confirma.
- Se o banco falhar, o Manager invalida o cache daquele documento em vez de exibir uma falsa baixa.
- Quando o Supabase está configurado, a cópia JSON local só é atualizada depois da confirmação online.
- O Manager aceita `SUPABASE_SERVICE_KEY` e dá prioridade a ela sobre `SUPABASE_KEY`.
- O Health Monitor mostra se a escrita está usando credencial de servidor ou chave anônima.
- `.gitignore` protege Secrets, caches, ZIPs, backups e principais JSONs operacionais em commits futuros.

## Etapa manual recomendada (R$ 0,00)

1. No Supabase, abra **Project Settings → API** e copie a chave `service_role`.
2. No Streamlit Cloud, abra os Secrets do app e adicione **somente lá**:
   `SUPABASE_SERVICE_KEY = "..."`
3. Reinicie o app e confirme no perfil Jorge que o Health Monitor mostra:
   **Banco: escrita protegida por credencial de servidor**.
4. Só depois execute `supabase_hardening_zero_cost.sql` no SQL Editor do Supabase.
5. Teste criar/editar uma proposta, reservar material e atualizar status.

> Nunca coloque a SERVICE KEY no GitHub, em arquivo `.py`, JSON, screenshot ou catálogo público.

## GitHub

O repositório do Manager deve ser **Private**. Isso não exige plano pago para um repositório privado comum.
O `.gitignore` impede novos commits acidentais, mas arquivos que já foram versionados anteriormente precisam ser removidos do rastreamento do Git em uma etapa controlada. Não apague os dados do Supabase.
