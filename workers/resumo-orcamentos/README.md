# AlphaFest — resumo diário de orçamentos para Telegram (preparação)

**Estado:** código somente no GitHub. **Não está publicado nem habilitado.**

Worker Cloudflare **novo e separado** de `alphafest-alertas` e `alphafest-novo`. Não modifica o Worker das visitas de cinco minutos.

## O que faz
- Às 09h de Brasília, em uma execução agendada diária (12:00 UTC), lê o documento `historico_orcamentos` da tabela privada `app_data` no Supabase.
- Reúne contagens de propostas **explicitamente marcadas como enviadas**, ainda não aprovadas, entregues ou encerradas.
- Mostra quantidade total, retorno há 1–2 dias, há 3+ dias, prazo de entrega até 2 dias/vencido e datas desconhecidas.
- Envia **somente contagens agregadas**, sem nomes, contatos, valores, números das propostas ou conteúdo das mensagens. A leitura usa credenciais privadas somente no Worker.
- Não marca atendimentos, não registra retornos, não envia mensagens aos clientes, não altera a base.

## Instalação futura (não realizada)
Criar um novo Worker em Cloudflare, usando esta pasta, sem substituir os Workers existentes. Configurar segredos **no painel do Worker**, nunca em código ou conversa:
- `SUPABASE_URL`: URL do Supabase
- `SUPABASE_SECRET_KEY`: credencial server-side com leitura da tabela privada `app_data` (idealmente restrita).
- `TELEGRAM_BOT_TOKEN`: token do bot.
- `TELEGRAM_CHAT_ID`: grupo privado correto.

O padrão no `wrangler.toml` é `QUOTE_SUMMARY_ENABLED=false`. Só depois de conferir leitura, autorização e destinatário corretos definir a variável para `true`. Não reutilizar o nome do Worker do site ou do alerta existente. O envio é silencioso (`disable_notification: true`).

## Limitações e controles
- A leitura do histórico inteiro exige confiança no segredo server-side; **não publicar o segredo**. O Worker ignora campos pessoais na mensagem final, mas recebe o documento inteiro para calcular contagens.
- O máximo é 10 mil propostas; a execução falha fechada acima desse limite.
- Esta rotina não possui trava de envio por data; reexecuções manuais ou retries podem duplicar mensagens. Não ative até haver controle operacional adequado.
- A classificação no JS é uma aproximação explícita do status do Manager; conferir equivalência com a fonte oficial antes de produção.
- Se o documento não existir ou vier inválido, **não envia alerta falso de zero**.
- O merge no GitHub não realiza deploy no Streamlit Cloud ou Cloudflare.

## Publicação
Acesso e publicação requerem o administrador da Cloudflare/Streamlit. Não é necessário mudar a configuração do Worker de alertas do site.
