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
- O identificador comercial do WhatsApp aceita o nome de campanha com o mesmo
  limite de **120 caracteres** do gerador de links. O teste E2E verifica
  uma campanha de 120 caracteres tanto na ficha quanto no carrinho.
- A navegação conserva o **primeiro toque UTM da sessão da aba**. O painel
  usa essa primeira campanha identificada e somente cliques de WhatsApp posteriores.
- Ao clicar no WhatsApp **dentro de uma ficha de produto**, o texto de orçamento
  ganha a linha `Referência da campanha: instagram/stories/natal-2026`
  (quando houver campanha UTM válida), sem duplicá-la em cliques repetidos.
- **Novo no carrinho HF65.24.52:** a mesma referência validada aparece no
  texto de orçamento com vários produtos, antes de abrir o WhatsApp.
  O cliente pode editar ou remover a referência na revisão. Se não houver
  campanha identificada, nenhuma referência é acrescentada; CTAs gerais
  permanecem inalterados. O carrinho conserva quantidades e observações
  existentes e NÃO envia mensagens automaticamente.
- Essa referência pode ajudar a comparar manualmente conversas recebidas
  com campanhas, **sem declarar vendas automaticamente**.
- Links antigos de produtos renomeados continuam a funcionar quando o nome
  anterior é mantido como **Alias não ambíguo** no Catálogo Oficial.
- Eventos de acesso não armazenam query strings, fragmentos nem caminhos externos
  detalhados do referenciador. A origem externa fica restrita ao domínio.
- Botões gerais de WhatsApp **não** herdam o nome do último produto visitado;
  somente CTAs dentro da ficha aberta ou da galeria identificam produto.
- Aproveita a tabela existente `site_metrics_events`, sem criar cadastro paralelo
  ou alterar status, orçamento, estoque, produção ou financeiro.

## Evidências automatizadas
- Execução GitHub Actions: https://github.com/jorgegaulke76-eng/alphafest-manager/actions/runs/44939143695
- 14 testes de regressão Python/JavaScript aprovados, incluindo a referência
  de campanha no WhatsApp da ficha, prevenção de duplicações, preservação do
  texto original e separação dos CTAs gerais.
- Navegador Chromium desktop e celular aprovado em cópia da vitrine real,
  verificando 92 slugs publicados, abertura/fechamento e CTA.
- API fictícia local: fluxo campanha -> produto -> WhatsApp -> página seguinte
  e cálculo do painel, sem envio de dados externos.
- **PostgREST + PostgreSQL descartáveis:** regras INSERT/SELECT/UPDATE testadas.
- **Navegador -> rastreador HF52 -> PostgREST real -> PostgreSQL temporário:**
  10 eventos de campanha persistidos em duas sessões independentes
  (desktop e celular), sendo por dispositivo 2 page_views, 1 product_open
  e 2 whatsapp_clicks (ficha e carrinho). O relatório conserva 1 sessão
  com WhatsApp por campanha, sem duplicar oportunidades por clique.
- O teste abriu o carrinho com 2 produtos, validou referência UTM no texto
  editável, a possibilidade de apagá-la e o envio simulado sem abrir serviços
  externos. Uma sessão sem campanha não recebeu referência indevida.
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
- [ ] Verificar manualmente se a mensagem recebida no WhatsApp contém a referência
      esperada, tanto na ficha quanto no carrinho, e se a mensagem continua editável;
      comparar a referência com o pedido pago antes de considerar uma
      venda atribuída à campanha.

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
