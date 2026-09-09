# Integração Meta — FestManager 5.6.0

Esta versão deixa a Central Multicanal pronta, mas **não ativa as contas automaticamente**. A ativação depende das credenciais empresariais da Alphafest no Meta Business.

## Arquitetura
Meta (WhatsApp / Instagram / Facebook) → Supabase Edge Function `meta-webhook` → documento `atendimentos_db` → Caixa unificada do FestManager.

## Publicação da Edge Function
1. No Supabase, crie/publique a função presente em `supabase/functions/meta-webhook/index.ts`.
2. Configure os segredos:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `META_VERIFY_TOKEN` (o mesmo mostrado em FestManager → Multicanal → Integrações Meta)
3. A URL ficará semelhante a `https://SEU-PROJETO.supabase.co/functions/v1/meta-webhook`.
4. No Meta for Developers, informe essa URL e o token de verificação.
5. Assine os campos de mensagens dos produtos/canais desejados.

## Segurança
- Nunca coloque o Service Role Key no GitHub.
- Não marque um canal como conectado antes de testar uma mensagem real.
- Respostas automáticas continuam desligadas até autorização explícita nas regras do FestManager.
