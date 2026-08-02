# FestManager 11.1.2 — Painel Operacional + Webhook Meta

## Painel da Anna
- Pedidos atrasados, entregas e aprovações agora possuem botão **Abrir e atualizar**.
- A proposta abre na própria Central do Dia.
- Anna pode marcar Aprovado, Pago e Entregue, registrar observação e salvar sem procurar a proposta em outra aba.
- Continua disponível o botão para carregar a edição completa.

## Integrações Meta
- Detecta quando `META_APP_ID` foi preenchido acidentalmente com um Client ID do Google.
- Sugere automaticamente a URL da Edge Function com base em `SUPABASE_URL`.
- Novo botão **Testar endpoint** valida URL e token como a Meta faz.
- Incluída Edge Function `supabase/functions/meta-webhook/index.ts` para receber WhatsApp, Instagram e Facebook e gravar as oportunidades no documento `atendimentos`.

## Segurança operacional
- O webhook é isolado do Streamlit: falhas externas não derrubam atendimento, orçamento ou histórico.
- Eventos duplicados são ignorados pelo ID externo.
- A função responde rapidamente à Meta e mantém cópia central no Supabase.
