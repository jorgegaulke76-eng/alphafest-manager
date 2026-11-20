# AlphaFest Manager — HF65.24.51 · Roteiros Práticos de Produção

## Objetivo

Facilitar o acompanhamento diário da Anna e a passagem de prioridades entre a equipe sem criar novos painéis, consultas ao banco ou filas de estoque.

## Recursos

- Em **Central de Pedidos → Planejamento diário**, botão **Baixar roteiro do dia (.txt)**. O arquivo reúne pedidos vencidos, para hoje, amanhã e sem prazo, com número, cliente, itens, etapa e ação sugerida. Pedidos de datas posteriores continuam acessíveis nos filtros, mas não entram na lista de urgências.
- Somente para **Jorge**, opção desmarcada por padrão para **incluir retornos comerciais com acompanhamento registrado**. Nenhuma mensagem é enviada e não são incluídos telefones, valores, meios de pagamento ou o texto das mensagens do WhatsApp.
- Em **Planejamento semanal**, botão **Baixar agenda da semana (.csv)**, compatível com Excel: separa vencidos, previstos nos próximos sete dias e sem prazo. Nomes que poderiam ser interpretados como fórmulas são escapados. A semana é contada a partir de hoje, como no painel homologado.
- Os downloads são gerados em memória a partir das filas atuais e não consultam Supabase nem modificam dados.

## Preservação e limites

- Status, pedidos, orçamento × catálogo, financeiro, WhatsApp, métricas e site preservados.
- Anna não recebe dados comerciais/financeiros adicionais nos downloads.
- Os arquivos são fotografias do momento: confirmar o andamento real na Agenda Oficial e na Central.
- Não há automatização, criação de pedidos, alteração de status ou envio de mensagens.

## Validação

30 testes automatizados (novos e regressão), compilação Python e verificação de integridade do ZIP. A interface final exige conferência no Streamlit publicado.

## Publicação

Atualizar apenas o Manager via GitHub Desktop: extrair ZIP no clone, Commit + Push. Sem alteração de Secrets, Supabase ou Cloudflare.
