# AlphaFest Manager — HF65.24.52 (candidata em homologação)

**Base preservada:** HF65.24.51 / `main`. Este documento não autoriza publicação automática.

## Objetivo
Conectar ações de divulgação do site aos produtos da vitrine e às oportunidades
de orçamento pelo WhatsApp, sem confundir um clique com uma conversa ou venda.

## Principais mudanças
- Gerador de links comerciais para produtos **efetivamente publicados**, a partir
  de lista pesquisável da vitrine, em cache por 10 minutos. Bloqueia seleção
  de produtos não disponíveis e descarta identificadores duplicados.
- Link `https://alphafest.com.br/?produto=<slug>&utm_source=...&utm_medium=...&utm_campaign=...`.
- Ficha abre automaticamente no destino indicado, respeitando o celular e
  permitindo fechar sem deslocamento horizontal.
- A navegação conserva parâmetros UTM dentro da sessão da aba. O painel
  usa a primeira campanha identificada e somente cliques de WhatsApp posteriores.
- Links antigos de produtos renomeados continuam a funcionar quando o nome
  anterior é mantido como **Alias não ambíguo** no Catálogo Oficial.
- Eventos de acesso não armazenam query strings, fragmentos nem caminhos externos
  detalhados do referenciador. A origem externa fica restrita ao domínio.
- Botões gerais de WhatsApp **não** herdam o nome do último produto visitado;
  somente CTAs dentro da ficha aberta ou da galeria identificam produto.
- Aproveita a tabela existente `site_metrics_events`, sem criar cadastro paralelo
  ou alterar status, orçamento, estoque, produção ou financeiro.

## Evidências automatizadas
- Execução GitHub Actions: https://github.com/jorgegaulke76-eng/alphafest-manager/actions/runs/44901604767
- 13 testes de regressão Python/JavaScript aprovados.
- Navegador Chromium desktop e celular aprovado em cópia da vitrine real,
  verificando 92 slugs publicados, abertura/fechamento e CTA.
- API fictícia local: fluxo campanha -> produto -> WhatsApp -> página seguinte
  e cálculo do painel, sem envio de dados externos.
- **PostgREST + PostgreSQL descartáveis:** regras INSERT/SELECT/UPDATE testadas.
- **Navegador -> rastreador HF52 -> PostgREST real -> PostgreSQL temporário:**
  8 eventos persistidos em duas sessões independentes (desktop e celular),
  com uma abertura e um clique por sessão, e análise UTM correta.
- Este último teste valida o contrato técnico em ambiente descartável.
  **Não é homologação da API Supabase hospedada nem prova de mensagens/vendas.**

## Checklist antes de liberar (exige conferência explícita)
- [ ] Revisar a PR e preservar cópia da versão 51 funcional.
- [ ] Em ambiente separado de produção, confirmar recebimento de eventos
      no Supabase hospedado, sem adicionar eventos falsos à tabela oficial.
      Não criar recursos pagos sem autorização.
- [ ] Aprovar visual e navegação em telefone físico, incluindo fechamento
      da ficha, filtros, botão de WhatsApp, carrinho e Galeria.
- [ ] Verificar que os produtos da campanha permanecem disponíveis.
- [ ] Conferir o resultado final do CI (todos os jobs verdes e sem conflitos).
- [ ] Obter aprovação para mesclar/publicar; não automatizar esse passo.
- [ ] Gerar prévia do site no Manager e publicar pelo fluxo Cloudflare existente.
- [ ] Após publicar, usar uma campanha real de divulgação e conferir os registros
      como **intenções de orçamento**, sem presumir mensagens enviadas.

## Critérios de reversão
Se ficha deixar de abrir, WhatsApp falhar, métrica duplicar ou desempenho piorar:
1. Suspender novas divulgações com links da HF52 até resolver.
2. Reverter a publicação do site para o snapshot anterior comprovadamente
   funcional (HF65.24.51), pelo procedimento já existente do Manager/Cloudflare.
3. Não apagar registros históricos de métricas nem tabelas Supabase.
4. Conservar os arquivos/links da campanha para comparação e depuração.

## Interpretação dos números
`page_view` = visita registrada; `product_open` = ficha aberta;
`whatsapp_click` = tentativa de abrir WhatsApp.
`sessoes_whatsapp` é a contagem de sessões com pelo menos um clique;
`cliques_whatsapp` pode ser maior pela repetição de ações.
**Nenhum indicador comprova contato iniciado, orçamento aceito, pedido pago
ou venda realizada.** Para medir faturamento por campanha, será necessário
conectar o encerramento de pedidos a um identificador de origem verificável
e obter a confirmação comercial, em etapa futura separada.
