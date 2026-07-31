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

## 3.2.2
- Logo e identidade da Alphafest centralizadas na barra lateral.
- Correção definitiva do nome ALPHAFEST.
- Botão Editar do catálogo abre um formulário visível e preenchido.
- Edição do catálogo mantém imagens locais e URLs existentes.

## 3.3.0
- Nova aba Configurações da Empresa.
- Dados da empresa, PIX e padrões de orçamento agora são configuráveis.
- WhatsApp, HTML da proposta, catálogo e barra lateral usam a configuração central.
- Número do WhatsApp do catálogo configurável.
- Novo arquivo empresa_config.json com fallback local e sincronização via Supabase.

## 3.4.0 — Central do Dia
- Nova aba Central do Dia como primeira tela do sistema.
- Saudação personalizada para Anna e Jorge.
- Os três e-mails informados possuem acesso administrativo completo.
- Identificação automática quando o login Google/OIDC do Streamlit disponibiliza o e-mail.
- Se o e-mail não estiver disponível, seletor simples de usuário na barra lateral.
- Indicadores de atrasados, entregas de hoje, aprovação, produção, pedidos prontos e valor previsto.
- Priorização automática do pedido que precisa de atenção primeiro.
- Central de alertas e pesquisa rápida por cliente, telefone, produto, tema ou pedido.

## 3.5.0 - Biblioteca Comercial 360°
- Catálogo ampliado com subcategoria e código interno.
- Descrições curta e completa.
- Preço, custo opcional e margem estimada.
- Tempo médio e processos de produção.
- Campos de personalização sugeridos.
- Conteúdo de marketing para redes sociais, Mercado Livre e Shopee.
- Upload de várias fotos por produto.
- Produto em destaque e preparação para publicação no site.
- Estatísticas de quantidade vendida, receita e última venda.
- Pesquisa por nome, categoria, subcategoria, código e palavras-chave.
- Compatibilidade preservada com os produtos já cadastrados.
