# AlphaFest — implantação segura do resumo diário no Telegram

**Estado atual (27/11/2026):** Worker `alphafest-resumo-orcamentos` ainda não implantado. Esta receita não altera `alphafest-alertas`, `alphafest-novo` nem o site.

## 1. Pré-condições (Cloudflare)
- Acesso ao painel Cloudflare da AlphaFest, com permissão de Workers e D1.
- O bot existente deve continuar no grupo privado de Jorge e Anna.
- No Supabase, a credencial usada deve ter permissão mínima de leitura de `app_data`; **não copiar tokens/chaves para GitHub ou chats**.
- O Manager em Streamlit Cloud é uma implantação **separada**. O merge do GitHub não prova que o app em uso foi atualizado.

## 2. Criar D1 sem mexer em banco comercial
1. Em Cloudflare → Workers & Pages → D1 SQL Database, criar banco com nome `alphafest-resumo-dedupe`.
2. Abrir o console SQL desse banco **novo** e executar o conteúdo de [schema.sql](schema.sql).
3. Anotar o ID real do D1 mostrado no painel Cloudflare (não é um Secret).
4. Na configuração do **novo** Worker, vincular D1 com binding exato `QUOTE_DEDUPE_DB`.
5. Confirmar que `quote_summary_delivery` tem `day_key` como PRIMARY KEY.

O arquivo [wrangler.toml](wrangler.toml) foi mantido sem ID de banco fictício. Caso a publicação seja feita por Wrangler, adicione antes do deploy:

```toml
[[d1_databases]]
binding = "QUOTE_DEDUPE_DB"
database_name = "alphafest-resumo-dedupe"
database_id = "SUBSTITUIR_PELO_ID_REAL_DO_D1"
```

**Não executar deploy** com `database_id` fictício e não vincular o banco de dados do site.

## 3. Criar Worker separado, inicialmente desligado
- Nome: `alphafest-resumo-orcamentos`.
- Código: [src/index.mjs](src/index.mjs).
- Cron Trigger: `0 12 * * *` (09h de Brasília).
- Variável `QUOTE_SUMMARY_ENABLED=false`.
- Binding D1: `QUOTE_DEDUPE_DB`.
- Secrets exclusivamente no painel do Worker: `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
- Não copiar as variáveis do Worker do site para arquivos de código. Não substituir o Worker de alertas de cinco minutos.

## 4. Portão de ativação
Antes de alterar `QUOTE_SUMMARY_ENABLED` para `true`:
- [ ] Worker e D1 novos criados; `schema.sql` aplicado.
- [ ] Confirmação de leitura do histórico real com autorização apropriada.
- [ ] Revisão da lógica de encerramento/aprovação com a fonte do Manager.
- [ ] Confirmação do ID do grupo privado, sem postar token.
- [ ] Conferência de que o Worker de cinco minutos segue intacto.
- [ ] Verificação dos testes de regressão em `src/index.test.mjs` (se dispensada, registrar risco).
- [ ] Ciência de que a proteção é **at-most-once**: uma falha após reserva impede tentativa automática no mesmo dia.

Só depois configurar `QUOTE_SUMMARY_ENABLED=true` no **novo Worker**. A ativação efetiva depende do painel da Cloudflare; commit e merge não enviam mensagens.

## 5. Confirmação do Manager no Streamlit Cloud
1. Abrir o aplicativo AlphaFest Manager pela URL de produção já conhecida da equipe.
2. Confirmar a existência da aba **Central de Oportunidades → Retornos de orçamentos** e do botão **Baixar resumo de retornos (.txt)**.
3. Se não estiverem presentes, verificar no Streamlit Cloud qual repositório, branch e commit alimentam o aplicativo e se a implantação está suspensa; não substituir arquivos JSON nem Secrets.
4. Evitar reboot/redeploy sem saber se há trabalhos ou formulários ainda em edição. O histórico permanece no Supabase.

## 6. Recuperação
- Para interromper o resumo diário: `QUOTE_SUMMARY_ENABLED=false`, **apenas no novo Worker**.
- Não apagar o D1 nem limpar `quote_summary_delivery` para forçar reenvio, pois isso pode gerar mensagens duplicadas.
- Os Workers `alphafest-alertas` e `alphafest-novo` e os dados do Manager não precisam ser alterados.

**Resultado esperado:** avisos de navegação a cada cinco minutos continuam como estão; um resumo agregado pode ser enviado uma vez por dia, somente após ativação.
