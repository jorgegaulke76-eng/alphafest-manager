# 20.4.9-I8.11.1 — Central de Faturamento Mensal
- Central mensal no perfil Jorge com competência, fechamento, faturado e recebido.
- Recebimento mensal atualiza automaticamente as propostas vinculadas.
- `faturamento_mensal_db.json` adicionado ao backup e integridade.
- Nenhuma alteração no Catálogo Oficial ou na fórmula de abatimento fixo homologada.

## 20.4.9-I8.11-HF2
- Extende para a Anna o fluxo comercial homologado no Jorge.
- WhatsApp reconhece cliente cadastrado e carrega o Perfil Comercial no modal de orçamento.
- Mensalista e abatimentos fixos em R$ passam a ser aplicados automaticamente nas novas propostas da Anna.
- Propostas da Anna salvam modalidade mensal, relacionamento e preço final aplicado sem alterar o Catálogo Oficial.
- Jorge permanece com a lógica HF1 homologada sem mudança de regra.

## 20.4.9-I8.11-HF1
- Hotfix da navegação: Novo Orçamento volta a abrir corretamente no perfil Jorge a partir de qualquer atalho/tela.
- Identificação automática de cliente por WhatsApp no Novo Orçamento do Jorge.
- Preenchimento de nome/documento e leitura imediata do Perfil Comercial cadastrado.
- Anna permanece sem esta extensão até homologação do Jorge.

## 20.4.9-I8.11
- Perfil Comercial do Cliente: faturamento mensal e abatimentos fixos em R$ por produto.
- Propostas mensalistas sem exigência de Pago individual; preço especial calculado sem alterar o Catálogo Oficial.

## 20.4.9-I8.10 — Inteligência Comercial dos Catálogos
- Nova aba de inteligência operacional de catálogos.
- Fila priorizada por validade, publicação, referências e divergência com o Catálogo Oficial.
- Novas publicações recebem assinatura SHA-256 irreversível do conteúdo comercial para detectar mudanças futuras sem armazenar preços antigos.
- Histórico consolidado de publicações e responsáveis.
- Sem telemetria fictícia: nenhuma métrica de clique/visualização é inferida sem fonte real.

## 20.4.9-I8.9.2.1 — Hotfix URL Supabase
- Corrige o project URL do visualizador público para `https://guejrwlblcxptzlobhit.supabase.co`.
- Links novos passam a carregar também `base=<SUPABASE_URL>` usando a configuração real do Manager.
- GitHub Pages valida que `base` é HTTPS e pertence a `*.supabase.co` antes de buscar o HTML.
- Links antigos continuam compatíveis pelo endereço oficial usado como fallback no `index.html`.
- QR Code, WhatsApp, PDF, validade, histórico e Catálogo Oficial permanecem inalterados.

## 20.4.9-I8.9.2 — Link Público via GitHub Pages
- Link do cliente passa a usar o GitHub Pages homologado da AlphaFest.
- Supabase Storage continua sendo o armazenamento dos HTMLs publicados.
- QR Code, WhatsApp, PDF e “Abrir catálogo” usam a mesma URL pública.
- Publicações antigas são migradas em leitura a partir do `object_path`, sem duplicação.
- Edge Function da I8.9.1 deixa de ser requisito.
- Validade comercial, usuário, histórico, Central, Modelos e Catálogo Oficial preservados.

## 20.4.9-I8.9.1 — Correção do link público

- Corrige o link público que abria o HTML como texto bruto no Supabase Storage.
- Mantém o HTML imutável no bucket `catalogo`, mas a URL enviada ao cliente passa pela Edge Function pública `catalogo-publico`.
- Edge Function aceita somente objetos da pasta `catalogos-publicos/` e responde com `text/html; charset=utf-8`.
- QR Code, WhatsApp, PDF e histórico passam a usar a URL renderizada.
- Publicações antigas com `object_path` são convertidas automaticamente para a nova URL, sem republicação.
- O Manager verifica a saúde da Edge Function antes de habilitar nova publicação e orienta a ativação quando ela estiver ausente.
- Nenhum preço, produto, foto, campanha ou banco comercial foi alterado.

## 20.4.9-I8.9 — Compartilhamento Profissional

- Central ganha painel de compartilhamento por catálogo salvo.
- Publicação cria URL pública real e única no Storage Supabase, sem sobrescrever versões anteriores.
- QR Code é gerado a partir do link público e pode ser baixado em PNG.
- Envio facilitado por WhatsApp com mensagem pronta, link e validade comercial.
- Link vencido é sinalizado e o sistema orienta publicar nova versão antes de enviar.
- PDF comercial gerado sob demanda, com data, usuário, validade de 30 dias, rodapé em todas as páginas e QR do link quando disponível.
- HTML passa a ter botão Imprimir / Salvar PDF; a versão pública também oferece Compartilhar.
- Publicações registram somente URL e rastreabilidade na Central; Catálogo Oficial continua sendo a única fonte de dados comerciais.
- Gerador oferece HTML e preparação de PDF sem executar processamento pesado a cada rerun.

## 20.4.9-I8.8.4 — Validade Comercial + Liberação Anna

- Todo catálogo HTML passa a exibir no rodapé data, horário e usuário da geração.
- Validade comercial automática de 30 dias a partir da geração.
- Aviso obrigatório no rodapé para reconfirmação de valores e condições após a validade.
- Catálogos salvos registram última geração, responsável e validade.
- `Gerar novamente com dados atuais` cria nova data de geração e renova os 30 dias.
- Central exibe status de validade, última geração, usuário e data limite.
- Ferramentas Gerador, Prévia, Modelos e Central liberadas para o perfil da Anna.
- Exclusão definitiva de catálogos e modelos permanece restrita ao Jorge.
- Catálogo Oficial segue como única fonte de preço, foto, descrição, material e campanha.

## 20.4.9-I8.8.3 — Modelos de Catálogo AlphaFest

- Nova biblioteca de modelos sem snapshot comercial.
- Modelos fixos: Completo, Sem Preços e Corporativo.
- Modelos automáticos por categoria e campanha do Catálogo Oficial atual.
- Modelos personalizados podem ser salvos, atualizados, duplicados, arquivados e restaurados pela Lixeira.
- Aplicar modelo recalcula os produtos elegíveis; nenhum produto é gravado dentro do modelo.
- Modelos personalizados entram no backup, integridade e auditoria.

## 20.4.9-I8.8.2 — Prévia Interna do Catálogo

- Prévia interna usa exatamente o mesmo HTML da exportação.
- Modos Celular e Computador no Gerador.
- Catálogo salvo pode ser aberto com prévia usando dados atuais do Catálogo Oficial.
- Editor mostra prévia das alterações antes de salvar.
- Nenhum snapshot comercial ou dado oficial é duplicado.

## 20.4.9-I8.7.1 — Homologação e Blindagem do Gerador de Catálogos

- Unifica categorias equivalentes somente na apresentação (ex.: BUBBLE/Bubble), sem alterar o Catálogo Oficial.
- Seleção individual segura para produtos com nomes repetidos.
- Blindagem de campos de lista, navegação HTML e WhatsApp.
- Mantém preço oficial como única fonte e `Preço sob consulta` quando ausente.
- Preserva integralmente os módulos homologados e a aba antiga de catálogo como fallback.

## 20.3.2 — Persistência das fotos locais do catálogo

- Corrigido o desaparecimento de fotos enviadas pelo computador após restart/deploy do Streamlit Cloud.
- Upload do catálogo continua priorizando o Storage do Supabase quando disponível.
- Se o Storage falhar, a imagem agora é otimizada e persistida como data URL dentro do registro do catálogo, em vez de apontar para arquivo temporário local.
- Fotos de fallback são reduzidas para até 1600x1600 e convertidas para WEBP para diminuir o peso do banco.
- Cadastro e edição informam que a imagem será incorporada ao catálogo.
- Google Drive, Marketing, Central de Campanhas, Template Engine e propostas permanecem inalterados.

## 12.0.2 — Interface Lean da Anna
- Barra horizontal de módulos removida no perfil da Anna.
- Central Operacional mantida como ambiente único e enxuto.
- Navegação administrativa do Jorge preservada integralmente.

## 10.0.2

- Corrigida a importação do Alpha Intelligence no Streamlit Cloud.
- O módulo agora fica na raiz para evitar falhas ao enviar pastas pelo GitHub.

# 9.2.0
- Cadastro Mestre e Alpha Connect Pro.
- IDs permanentes e vínculos intermodulares.
- Diagnóstico seguro das integrações.

# 9.1.1

- Corrige geração de campanhas com imagens do catálogo armazenadas por URL, caminho, bytes ou Base64.
- Adiciona diagnóstico Alpha Connect em Configurações.
- Mantém upload livre isolado dos dados do catálogo.

# 8.2.1

- Corrigida a falha de inicialização causada pela ausência de `STATUS_FLUXO`.
- Criado `constants.py` para centralizar status e prioridades do fluxo de pedidos.
- Iniciada a modularização segura sem alterar dados ou comportamento do Creative Studio.

# FestManager 7.0.0 — Relacionamentos e Política de Atendimento

- Novo núcleo de Relacionamentos no lugar do cadastro isolado de clientes.
- Papéis múltiplos por pessoa ou empresa, incluindo cliente e fornecedor simultaneamente.
- Controle individual de atendimento manual, assistido, automático, monitorado ou bloqueado.
- Permissões para catálogo, orçamento, campanhas e respostas.
- Pagamento antecipado e aprovação do gestor configuráveis.
- Cadastro de materiais, prioridade, prazo e avaliação de fornecedores.
- Alpha e Central Multicanal respeitam as restrições comerciais.
- Migração aditiva para a versão de dados 4, sem apagar registros.

# 5.6.0
- Central Multicanal e preparação oficial dos webhooks Meta.
- Caixa unificada e filtros por origem.
- Teste de entrada e configuração segura.

# FestManager 5.4.0 — Assistente Operacional

- Central do Dia com as cinco prioridades mais importantes.
- Ordenação por SLA, prazo e etapa operacional.
- Atalho para WhatsApp em atendimentos priorizados.
- Cartão do cliente com ticket médio, itens mais solicitados, temas recorrentes e próxima ação.
- Nenhuma migração e nenhum arquivo de dados incluído.

# FestManager 4.2.1 — Desempenho e Cache Inteligente

- Cache temporário por sessão para documentos do Supabase.
- Redução de leituras repetidas durante os reruns do Streamlit.
- Atualização imediata do cache após salvar dados.
- Expiração em 20 segundos para sincronização entre computadores.
- Teste de conexão em cache por 30 segundos.
- Reutilização de conexão HTTP com o Supabase.
- Timeout de rede reduzido para evitar telas presas em falhas de conexão.
- Nenhum arquivo de dados incluído ou substituído.

# CHANGELOG

## 4.0.1 — Proteção de Dados e Backup Automático
- Backup automático diário no primeiro acesso após o horário configurado.
- Backup manual completo e protegido.
- Retenção configurável dos backups automáticos.
- Histórico, download ZIP, verificação de integridade e restauração controlada.
- Backup de segurança automático antes de restaurações.
- Separação entre versão do aplicativo e versão dos dados.

hangelog

## 4.0.0 — Operação Inteligente
- Atendimento vinculado automaticamente à proposta criada.
- Linha do tempo automática dentro de cada atendimento.
- Mudanças de status podem atualizar o Fluxo de Pedidos.
- A Central do Dia prioriza atendimentos com SLA vencendo.
- Proposta criada pela fila mantém vínculo com o contato original.

# Versão 3.9.1 — Central de Atendimento e CRM Evolutivo

- Nova aba Central de Atendimento com fila, prioridades e tempo de espera.
- Modos Manual, Assistido e Automático, com regras independentes por tipo de mensagem.
- Respostas sugeridas editáveis e botão para abrir a conversa no WhatsApp.
- Registro manual de contatos enquanto a integração oficial do WhatsApp não estiver conectada.
- Atalho para iniciar orçamento a partir do atendimento.
- Central do Dia mostra atendimentos pendentes, pedidos de orçamento, catálogos e contatos há mais de 30 minutos.
- Cadastro de clientes evolutivo: apenas nome/identificação é necessário; os demais dados são opcionais.
- Perfis comerciais múltiplos, interesses, campanhas, potencial, cidade e origem do cliente.
- Perfis/segmentos comerciais editáveis pelo próprio sistema.
- Novos bancos `atendimentos_db.json` e `segmentos_db.json`, sincronizados pelo Supabase com fallback local.
- Integração automática com WhatsApp preparada, mas ainda depende da WhatsApp Business Platform e webhook oficial.

# Versão 3.8.0 — Assistente Comercial

- Calendário Comercial Inteligente com campanhas nacionais, locais, internas e personalizadas.
- Cadastro livre de volta às aulas, férias, eventos escolares, campanhas da cidade e datas próprias.
- Campanhas recorrentes anuais ou eventos únicos.
- Alertas por antecedência configurável.
- Outubro Rosa, Novembro Azul e outras campanhas iniciais editáveis.
- Oportunidades comerciais exibidas na Central do Dia.
- Produtos, região, observações e status ligados a cada campanha.
- Persistência no Supabase com fallback em `campanhas_db.json`.

# Versão 3.7.0 — Memória da Empresa

- Caixa do Projeto vinculada a cada proposta.
- Upload individual de artes, arquivos de produção, fotos finais, vídeos e referências.
- Observações, tags, arquivo mestre, favoritos e arquivamento.
- Nova aba Memória com pesquisa por cliente, tema, produto, pedido, arquivo e tag.
- Projetos podem ser marcados como modelos reutilizáveis e duplicados em novo orçamento.
- Novo banco projetos_db.json, sincronizado pelo Supabase com fallback local.

# CHANGELOG — FestManager

## 3.6.2 — Correção de inicialização
- Importação resiliente da camada `cloud_db.py`, evitando falha total em atualizações parciais.
- Fallback automático para JSON local quando uma função online estiver ausente ou indisponível.
- Correção da importação de `Path`, necessária para arquivos e artes.
- Mantido o fuso `America/Sao_Paulo` em todas as datas exibidas.
- `cloud_db.py` agora declara explicitamente as funções públicas usadas pelo aplicativo.
- Biblioteca de arquivos, artes e fotos preservada.

# Versão 3.6.1 — Estabilidade e Memória do Produto

- Corrige datas e saudações para o fuso configurável `America/Sao_Paulo`.
- Adiciona upload individual de arquivos em cada produto.
- Permite classificar, descrever, etiquetar, favoritar e arquivar arquivos.
- Pesquisa do catálogo encontra nomes, tags e descrições dos anexos.
- Armazenamento no Supabase Storage com fallback local.
- Mantém compatibilidade com produtos e dados antigos.

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

## 3.5.1 — Preenchimento automático gratuito
- Gerador automático de descrição curta e completa sem API paga.
- Geração de palavras-chave, legenda social e hashtags.
- Geração de descrições para Mercado Livre e Shopee.
- Botões para gerar tudo, somente descrições ou somente marketing.
- Campo de características-base salvo junto ao produto para reutilização.

## 3.9.2 — Caixa de Entrada Inteligente

- Contador de atendimentos pendentes no título da aba.
- Fila ordenada automaticamente por SLA e tempo de espera.
- Indicadores separados para atendimentos em atenção e urgentes.
- Configuração dos limites de SLA em minutos.
- Responsável por atendimento: Anna, Jorge ou sem responsável.
- Filtro por responsável.
- Próxima ação sugerida conforme o status da conversa.
- Atalhos para responder, criar orçamento, aguardar cliente, concluir e arquivar.
- Resumo de atendimentos pendentes na barra lateral.
- Correção do link do WhatsApp para números que já incluem o código do país.


## 4.2.0 — Núcleo Profissional
- Migrações automáticas aditivas e versionadas.
- Auditoria de backups, migrações, exclusões e restaurações.
- Lixeira recuperável para propostas, produtos, clientes e campanhas.
- Diagnóstico de Supabase, integridade, backup e versão de dados.
- Preparação segura de atualização com backup protegido.
- Pacote de atualização sem arquivos de dados.

## 4.3.0 — Produtividade Operacional e Pesquisa Global

- Pesquisa global sob demanda em clientes, propostas, catálogo, atendimentos, projetos e arquivos.
- Pesquisa rápida disponível na barra lateral em todas as telas.
- Ações rápidas para orçamento, WhatsApp, proposta e catálogo.
- Nova fila operacional na Central do Dia.
- Priorização automática por SLA, atraso, entrega e estágio de produção.
- Próxima ação sugerida para cada pendência.
- Sem migração ou substituição de dados.


## 4.4.0
- Assistente de Projeto Personalizado baseado na necessidade do cliente.
- Quantidade livre e sem mínimo obrigatório.
- Descrição livre de materiais, cores, tamanhos, acessórios e acabamentos.
- Integração do briefing com orçamento e Memória da Empresa.

## 5.0.0 — Base de Conhecimento
- Biblioteca viva de componentes e características.
- Categorias e opções criadas diretamente pela equipe.
- Componentes vinculados aos projetos realizados.
- Pesquisa por material, cor, formato, acessório, técnica, tema e característica livre.
- Backup e pesquisa global atualizados para incluir a base de conhecimento.

## 5.1.1 — Centro de Trabalho
- Adicionadas ações rápidas na Central do Dia.
- Adicionado resumo operacional do dia.
- Adicionada Minha Fila por usuário e prioridade de SLA.
- Nenhuma alteração ou migração nos dados existentes.

## 5.2.0
- Fluxo Atendimento → Projeto → Orçamento → Produção.
- Aprovação explícita de propostas.
- Próxima ação e linha do tempo integradas.

## 5.3.0 — Jornada Única de Atendimento
- Adicionada a aba **Jornada** para conduzir cliente, necessidade, solução e proposta em uma única tela.
- Incluído indicador de progresso do atendimento.
- Incluído salvamento de rascunho na Memória da Empresa.
- Incluída criação conjunta e vinculada de projeto e proposta.
- Mantidos os módulos anteriores para compatibilidade e operação gradual.
- Nenhuma migração destrutiva e nenhum arquivo de dados incluído.

## 5.5.0 — Painel Executivo
- Adicionada a aba Executivo com visão comercial, financeira e operacional.
- Incluídos indicadores de conversão, ticket médio, valores do dia e pendências financeiras.
- Incluídos semáforos de saúde da empresa e alertas gerenciais.
- Incluídos gráficos mensais de orçamentos e produtos mais solicitados.
- Mantida a versão de dados 3, sem migração ou alteração destrutiva.


## 5.7.0 — CRM Inteligente
- Funil comercial, Índice Alpha, temperatura, próxima ação e priorização de oportunidades.
- Atualização rápida de etapa e responsável.
- Correção do filtro por canal na caixa multicanal.

## 6.1.0 — Alpha Assistente Comercial
- Criada a aba Alpha para organizar mensagens recebidas.
- Adicionada interpretação local e explicável do pedido.
- Adicionado checklist dinâmico de perguntas faltantes.
- Adicionadas respostas assistidas e pesquisa de referências internas.
- Integração com Jornada e Projeto Personalizado.

## 8.1.0 — Central de Crescimento
- Adicionada Central de Crescimento com geração imediata de conteúdo multicanal.
- Adicionada fila de campanhas e histórico de publicação.
- Propostas antigas passam a receber relacionamento_id por correspondência segura de documento, WhatsApp ou nome exato.
- Indicadores dos relacionamentos passam a considerar todas as propostas vinculadas.
- Migração de dados aditiva para v5.

## 9.0.0 — Base Modular Estável
- Corrigidas constantes ausentes do Fluxo de Pedidos.
- Corrigidas referências da configuração da empresa no Creative Studio.
- Versão e configurações estáveis movidas para `config.py`.
- Iniciada a arquitetura `services/` e `modules/`.

## 9.0.1
- Corrigida duplicidade segura de relacionamentos originada por propostas antigas sem telefone/documento.
- Relacionamentos passaram a ser a fonte atual de dados pessoais nas propostas.
- Histórico, HTML e WhatsApp usam os dados atuais sem alterar o conteúdo comercial histórico.

## 9.1.0 — Creative Studio Premium
- Upload livre totalmente separado do catálogo, sem reaproveitar produto ou descrição anterior.
- Nome e descrição da imagem obrigatórios no modo livre.
- Geração opcional de copy por IA via OpenAI, com fallback local seguro.
- Identidade Alphafest aplicada automaticamente nas artes PNG.
- Cards por canal com logotipos das plataformas, resolução, formato e status.
- Upload opcional de vídeo curto preservado para Reels, TikTok e Shorts.
- Aprovação individual mantida e envio em lote de todos os canais aprovados para a fila de publicação.
- Registro explícito de que publicação automática depende das credenciais oficiais das redes.

## 11.1.0
- Central de Oportunidades isolada e protegida.
- Migração de contatos externos para atendimento no WhatsApp.
- Fonte da venda por canal, conteúdo, campanha e produto.
- Funil e conversão por canal.
- Ranking de conteúdos por contatos, orçamentos, vendas e faturamento.

## 11.1.1 — 02/08/2026
- Novo Painel da Anna com prioridades operacionais e indicadores por canal.
- Diagnóstico das Integrações Meta unificado com os Secrets do Alpha Connect.
- Separação visual entre credenciais configuradas e webhook realmente validado.


## 12.0.1
- Atualização completa da Central do Dia após salvar andamento de proposta.
- Limpeza do estado do editor anterior para impedir dados repetidos na proposta seguinte.

## 13.2.0 — THU prático e Alpha Marketing Instagram
- Prioridades objetivas no briefing executivo do THU.
- Indicadores executivos compactos.
- Alpha Marketing restaurado com Instagram como canal principal.
- Facebook removido da geração separada; replicação pela Meta.
- Central da Anna preservada.


## 14.2.5
- Corrigido falso alerta de `componentes_db`.
- Adicionado Health Monitor compacto e exclusivo da Central do Jorge.

## 15.0.0 — AlphaFest Design System
- Criada biblioteca visual `alphafest_design_system.py`.
- Aplicada identidade oficial azul e branca ao Alpha Marketing Studio.
- Padronizados tamanhos de títulos, textos, labels, botões e abas.
- Reorganizada a criação de campanha em duas colunas, com preview compacto.
- Mantidas as rotinas existentes de geração, biblioteca e exportação.

## 19.0.2 — Correção de versão e deploy
- Versão exibida agora é lida de `VERSAO.txt`.
- Template Anna e `photo_mode` validados no fluxo real do Marketing Studio.

## 19.1.0 — Splash Premium AlphaFest
- Novo template oficial baseado no modelo aprovado pela AlphaFest.
- Aplicações do produto e composição comercial premium.

## 19.1.2 — Correção de composição Splash Premium
- Preço isolado em área própria, sem sobreposição.
- Faixa de aplicações redimensionada.
- CTA, foto e rodapé reposicionados para melhor equilíbrio.

## 20.0.0 — Template Engine
- Biblioteca de templates externos por pasta/ZIP.
- `layout.json` com zonas normalizadas e renderização genérica.
- Primeiro template: Anna Base Dinâmica.
- Importar/exportar templates sem novo deploy.

## 20.1.0
- Propostas: novos motivos de não fechamento por falta de pagamento e falta de retorno.
- Marketing: separação entre Produzir Campanha e Template Studio.
- Template Engine 20.0 preservado sem alteração dos templates instalados.

## 20.1.1 — Hotfix estabilidade de propostas
- Corrigido `StreamlitDuplicateElementKey` na Central Operacional da Anna.
- As caixas “Não fechado — falta de pagamento” e “Não fechado — sem retorno do cliente” agora usam chaves exclusivas por contexto e proposta.
- Preservados Marketing 20.1.0, Template Engine 20.0.0 e templates instalados.

## 20.2.0
- Marketing: novo Modo Produção Rápida com fluxo Produto → Template → Campanha → Gerar.
- Catálogo passa a preencher preço automaticamente no modo rápido.
- Calendário Mestre controla tema/paleta automaticamente.
- Ajustes opcionais concentrados em um único painel rápido.
- Template oficial `anna_base_dinamica` preservado.

## 20.3.0 — Central de Campanhas
- Nova Central de Campanhas com busca, filtros, favoritas e miniaturas.
- Upload de artes prontas para postagem como referências reutilizáveis.
- Campanhas criadas pelo AlphaFest agora guardam preço, CTA, chamada e origem criativa.
- Reutilização rápida cria nova versão editável alterando preço, CTA, chamada e formatos.
- Duplicações preservam a campanha original e registram a origem.
- Template Engine, Anna Base Dinâmica e hotfix das propostas preservados.

## 20.3.4 - Exibição das fotos persistentes do Catálogo
- Decodificação de data URLs/base64 antes do `st.image()`.
- Correção da visualização na listagem, modal e edição do produto.
- Catálogo HTML passa a aceitar data URLs incorporadas diretamente.

## 20.4.0 - Motor de Renderização de Precisão
- Clipping por zona, auto-fit de fontes, foto proporcional e zonas seguras para telefone/preço/CTA.
- Anna Base Dinâmica preservada; apenas regras de posicionamento e comportamento foram refinadas.


## 20.4.1 — Hierarquia Visual Segura
- Ajustes tipográficos sem alterar os formatos/canais.


## 20.4.2
- Calibração Visual Anna.
- VERSAO.txt e VERSAO sincronizados.


## 20.4.3
- Recalibração conservadora das zonas do Feed no Anna Base Dinâmica.

## 20.4.9-I8.8 — Central de Catálogos AlphaFest
- Gerador I8.7.1 passa a salvar configurações reutilizáveis na nova Central de Catálogos.
- Catálogos salvos guardam referências e configuração, sem duplicar preço, foto, descrição ou material do Catálogo Oficial.
- Nova gestão com abrir, editar, duplicar, gerar novamente, arquivar/reativar e excluir com Lixeira.
- Geração posterior sempre consulta os dados atuais do Catálogo Oficial.
- Referências não resolvidas são sinalizadas como pendentes, sem substituição silenciosa.
- Central incluída no backup completo, integridade e auditoria do sistema.


## 20.4.9-I8.8.1
- Hotfix de usabilidade: Lixeira de catálogos agora visível dentro da Central I8.8.
- Indicador de quantidade na lixeira, restauração e exclusão definitiva com confirmação.
- Lixeira geral do sistema preservada.

## 20.4.9-I8.10.1 — Refinamento Operacional da Inteligência
- Fila inteligente ganha Publicar/Republicar em um clique.
- Filtros combináveis por situação, prioridade e validade.
- Novas publicações registram hashes individuais por produto, sem snapshots comerciais.
- Mudanças futuras podem apontar o produto envolvido e abrir o cadastro para revisão pelo Jorge.
- Anna mantém acesso à Inteligência e vê o produto alterado, sem ganhar permissão técnica de edição do Catálogo Oficial.
- Motor de detecção I8.10, Central, validade, QR, WhatsApp, PDF, Supabase e GitHub Pages preservados.

## 20.4.9-I8.11.1-HF2 — Fechamento comercial e reabertura auditada
- Propagação de recebimento mensal agora aparece corretamente na proposta como Pago no fechamento mensal.
- Fechamento mensal ganhou mensagem de WhatsApp, HTML, PDF e observação comercial.
- Reabertura permitida após Fechado, Faturado ou Recebido, sempre com motivo e histórico auditável.
- Recebimentos já registrados são preservados; correções posteriores calculam saldo adicional ou crédito do cliente.
- PDF do fechamento é preparado somente sob demanda.
- Homologação desta etapa continua restrita ao perfil Jorge.
