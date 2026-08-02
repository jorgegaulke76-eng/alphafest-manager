# Ativar captação real da Meta

1. Instale o Supabase CLI e faça login.
2. Na pasta do projeto execute:
   `supabase functions deploy meta-webhook --no-verify-jwt`
3. Cadastre os segredos da função:
   `supabase secrets set META_VERIFY_TOKEN="O_MESMO_TOKEN_DA_TELA"`
   O Supabase já fornece `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY` à função hospedada.
4. No FestManager, abra **Multicanal → Integrações Meta** e clique em **Testar endpoint**.
5. No Meta for Developers, informe a URL exibida e o mesmo token de verificação.
6. Assine os eventos necessários de WhatsApp, Página/Facebook e Instagram.
7. Envie uma mensagem real e confira a entrada em **Caixa unificada**.
8. Somente depois marque o webhook do canal como validado.

## Atenção
`META_APP_ID` deve ser o ID numérico do aplicativo Meta. Um valor terminado em `apps.googleusercontent.com` pertence ao Google/YouTube e está incorreto para esta integração.
