# CHANGELOG

## 3.2.0 — Produção

- Nova aba Produção integrada às propostas.
- Tarefas automáticas por item do orçamento.
- Setores e subgrupos de balões configurados.
- Grupos livres para Papelaria, 3D, Lembrancinhas e Gráfica rápida.
- Status, prioridade, responsável e observações internas.
- Filtros por prazo, setor, status, prioridade e pesquisa.
- Indicadores de atrasos, entregas de hoje, itens em produção e prontos.
- Ao concluir todos os itens, a proposta é marcada como entregue.
- Persistência no Supabase com fallback em producao_db.json.

# Alphafest Manager — Changelog

## 3.1.0
- Novo módulo Clientes.
- Sincronização automática de clientes a partir do histórico.
- Cadastro, edição, exclusão e pesquisa de clientes.
- Resumo financeiro e histórico de propostas por cliente.
- Novo orçamento com dados do cliente preenchidos.
- Backup independente de clientes.

## 3.0.0
- Orçamentos, histórico, relatórios e catálogo integrados.
- Supabase com fallback JSON.
- Catálogo personalizado para consulta do cliente.

## 3.2.1 — Fluxo de Pedidos
- Substituído o modelo de setores pelo fluxo real do pedido.
- Nova aba “Fluxo de Pedidos” com Visão geral, Artes, Produção e Prontos/entregas.
- Etapas da arte até a entrega, sem nomes de funcionários.
- Processos múltiplos: arte, impressão, laser, 3D, balões, montagem, acabamento e entrega.
- Linha do tempo automática por item.
- Indicadores de atrasos, entregas do dia, aprovação, produção e pedidos prontos.
- Pesquisa por cliente, pedido, produto, tema, nome, telefone e detalhes.
