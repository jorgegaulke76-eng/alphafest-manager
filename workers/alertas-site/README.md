# 🔔 AlphaFest — avisos sonoros de acessos (opcional)

**Estado: PR de preparação; não instalado e sem envios ativados.**

## Objetivo
Usar os eventos do site que o Manager já grava na tabela privada \`site_metrics_events\`. Um Cloudflare Worker **separado** (nome sugerido: \`alphafest-alertas\`) consulta, a cada 5 minutos, a janela anterior de eventos e envia **um aviso com totais** para um grupo privado no Telegram quando houver acessos ou cliques para WhatsApp. A Anna e Jorge entram no mesmo grupo.

- Não injeta scripts novos no site, não altera PWA nem DNS, não modifica pedidos ou produtos.
- Sem identificar visitantes: a mensagem traz só contagens de eventos/sessões; não inclui nomes, IPs, URLs, telefones ou IDs.
- Não é identificação de humanos: robôs que executam JavaScript podem gerar registros; URLs técnicas evidentes são filtradas.
- Atraso: 0 a 5 minutos; cron e rede podem acrescentar atraso. Não garante 100% das visitas (bloqueadores de rastreamento etc.).
- Só gera avisos com \`ALERTS_ENABLED=true\`; padrão é **desligado**. Não há custo de API paga do WhatsApp.
- \`disable_notification=false\` pede aviso sonoro ao Telegram; depende do som/Do Not Disturb configurado em cada celular.
- Não há endpoint público para forjar mensagens, nem tokens no HTML ou GitHub.

## Preparar nos celulares (sem enviar segredos no chat)
1. Instalar Telegram nos dois celulares.
2. No Telegram, criar um bot pelo [@BotFather](https://t.me/BotFather), e um **grupo privado AlphaFest | Alertas** com Anna, Jorge e o bot.
3. Enviar uma mensagem no grupo e obter o ID numérico do grupo pelo método oficial \`getUpdates\` do bot. Não colar o token no GitHub ou nesta conversa.
4. Personalizar o som do grupo no Telegram em cada celular.

## Habilitar quando os destinatários estiverem configurados
1. Criar um Worker separado no painel Cloudflare / Wrangler usando o diretório deste projeto; não substituir \`alphafest-novo\` nem mexer no Worker do site.
2. Definir como **secrets criptografados**, nunca como texto do repositório:
   - \`SUPABASE_URL\` — URL do Supabase já utilizado pelo Manager.
   - \`SUPABASE_SECRET_KEY\` — chave **server-side** que consiga ler a tabela privada de métricas.
   - \`TELEGRAM_BOT_TOKEN\` — chave do bot privado.
   - \`TELEGRAM_CHAT_ID\` — ID numérico do grupo privado.
3. Validar conectividade e leitura de métricas sem expor segredos. Confirmar o bot no grupo.
4. Alterar \`ALERTS_ENABLED\` para \`true\` **somente depois** do aceite. O cron \`*/5 * * * *\` funciona em UTC, mas a janela de cinco minutos e o horário mostrado em Brasília são consistentes.
5. Para desligar, definir \`ALERTS_ENABLED=false\`. O site e o Manager continuarão sem alteração.

## Verificação sem credenciais
Na pasta \`workers/alertas-site\`, executar \`node --test src/index.test.mjs\`. Os testes usam dados fictícios e substituem todas as chamadas de rede.

## Segurança e limites
- A chave Supabase privilegiada **nunca** pode ficar em arquivo estático público, variável de front-end ou commit. Recomendável uma credencial exclusivamente de leitura se disponível. Os segredos ficam vinculados ao Worker.
- A janela é fixa e sem sobreposição: a cada 5 min há no máximo uma execução programada, mas retry manual/atrasos de infraestrutura podem gerar perda ou duplicação de aviso; não usar alertas como auditoria.
- Consultas são limitadas a 1000 eventos/intervalo; o texto indica contagem parcial se chegar nesse limite.
- Este é um recurso de conveniência operacional, não emergência ou segurança.

## Melhoria: destacar interesses comerciais (preparada em novembro de 2026)

O bot continua mandando **no máximo um alerta por execução de 5 minutos**,
sem repetir mensagens quando surgem vários cliques no mesmo intervalo.

- **🚨 Clique no WhatsApp detectado:** prioridade comercial; pede para conferir
  conversas, mas avisa que o clique **não comprova mensagem, pedido ou venda**.
- **🎁 Produtos consultados:** destaque de interesse, se não houver clique no WhatsApp.
- **🔔 Visitas:** resumo normal quando ocorrer apenas navegação.

O som continua definido pelo Telegram em cada celular. **Não é possível garantir
um toque diferente para apenas uma mensagem no mesmo grupo.** Essa alteração
muda o texto, não a configuração do áudio.

### Como aplicar ao Worker já criado

1. Abra o **mesmo** Worker `alphafest-alertas` na Cloudflare.
2. Clique em **Edit code**. Substitua o conteúdo do arquivo principal pelo
   [código atualizado](https://raw.githubusercontent.com/jorgegaulke76-eng/alphafest-manager/main/workers/alertas-site/src/index.mjs).
3. Salve em **Deploy**; não altere Secrets, Cron Triggers, nome do Worker, ou
   o Worker do site `alphafest-novo`.
4. Se o Worker estava ativo, os novos avisos passam a usar o texto atualizado
   no próximo ciclo em que houver eventos.

Uma alteração no GitHub **não** atualiza automaticamente o Worker da Cloudflare.
Não reenviar tokens para GitHub, chats ou navegador público.
