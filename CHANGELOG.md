
## 20.4.9-I8.13.5-HF26 — THU • Plano de amanhã
- Reaproveita a prevenção da HF25 para preparar o próximo dia.
- Separa ações em Produção, Materiais e Saídas.
- Inclui pedidos já Prontos com saída prevista para amanhã.
- Não repete atrasos nem pedidos não Prontos que já são urgência de hoje.
- Somente leitura; sem alteração de bancos operacionais.
# 20.4.9-I8.13.5-HF21 — THU • Sem avanço registrado

- Novo radar somente leitura no perfil Jorge usando as fotografias diárias da Agenda da Anna.
- Sinaliza prazo hoje/vencido sem mudança de status desde a abertura e recorrência da mesma fase por 2+ dias.
- Não presume ausência de trabalho físico; o alerta significa somente ausência de mudança de status registrada.
- Nenhum status, contato ou mensagem é alterado automaticamente.

# 20.4.9-I8.13.5-HF20 — Agenda Atualizável da Anna
- Mantém o roteiro da manhã congelado para comparação.
- Adiciona PDF atualizável a qualquer momento do dia, usando o banco atual.
- Nome do arquivo inclui horário para diferenciar impressões sucessivas.
- Nenhuma alteração automática em pedidos ou status.

# 20.4.9-I8.13.5-HF19 — Fechamento Diário Comparativo da Anna
- Agenda da Anna passa a registrar uma fotografia explícita do início do dia para servir como linha de base.
- Fechamento compara a situação atual com a manhã e separa entregues, avanços de status, novos pedidos e pendências que seguem abertas.
- PDF de fechamento é somente dados, sem imagens e sem alterar qualquer pedido.
- Fotografia diária usa o mesmo banco `app_data`, sem nova tabela/SQL, com retenção de 60 dias.
- Os 28 JSON/SQL existentes da HF18 permanecem intactos; apenas um novo documento de snapshot é adicionado.

# 20.4.9-I8.13.5-HF15 — THU • Cobranças Assistidas
- Segunda etapa do ciclo de inteligência assistida, ainda somente no perfil Jorge.
- Central cria fila financeira para pedidos aprovados e não pagos, excluindo faturamento mensal.
- THU prioriza entregues/prontos/prazos próximos e tempo desde a última cobrança registrada.
- WhatsApp é apenas preparado; **Registrei cobrança** não altera o status Pago.
- Confirmação oficial de Pago remove automaticamente o pedido da fila financeira.

# 20.4.9-I8.13.5-HF14 — THU • Retornos Comerciais
- Primeiro passo do novo ciclo de automações/inteligência, homologado primeiro no perfil Jorge.
- Envio/retorno de orçamento passa a ter registro explícito, sem presumir que abrir o WhatsApp significa enviar.
- THU ordena propostas enviadas ainda não aprovadas por tempo sem retorno e proximidade do prazo.
- WhatsApp de acompanhamento é apenas sugerido/aberto; nenhum envio ou mudança de status ocorre automaticamente.
- Central da Anna permanece preservada nesta etapa.

## 20.4.9-I8.13.3 — Núcleo de Integridade e Segurança (custo zero)
- Persistência confirmada antes do cache.
- Preparação para SERVICE KEY e RLS fechado.
- Health Monitor com estado da última gravação.
- Higiene de deploy e proteção de Secrets.

## 20.4.9-I8.13.2-CAT1-HF12 — Proposta pública sem duplicidade/CPF
- Evita `ITATIBA ITATIBA` no cabeçalho quando a cidade já estiver incorporada ao nome público da empresa.
- Remove CPF/CNPJ anexado ao campo `Empresa` somente na saída pública da proposta/WhatsApp, preservando a configuração interna.

## 20.4.9-I8.13-HF2 — Proveniência real do Pronto
- Corrige definitivamente o falso **“Pronto hoje”** em pedidos legados.
- `pronto_em` só é usado para calcular espera quando possui o marcador interno `pronto_em_confiavel`, criado exclusivamente numa transição real de Pronto observada pela versão atual.
- Carimbos antigos sem proveniência passam a ser tratados como **data de conclusão não registrada**, mesmo que o campo `pronto_em` esteja preenchido.
- Novos acionamentos de Pronto gravam `pronto_em`, `pronto_por` e a proveniência no mesmo salvamento oficial.
- Histórico de entregas mantém a ordenação correta da HF1: datas reais mais recentes primeiro e registros sem data real no final.
- Nenhuma migração destrutiva e nenhum JSON operacional alterado no pacote.

## 20.4.9-I8.13-HF1 — Datas reais + Histórico correto
- Novos registros de Pronto passam a gravar `pronto_em` e `pronto_por` na proposta oficial.
- Pedidos Pronto sem data histórica confiável não recebem fallback inventado; a Central informa data de conclusão não registrada.
- Indicador 3+ dias considera apenas tempo de espera calculável a partir de `pronto_em`.
- Histórico de Entregues passa a ordenar por data real (`entregue_em`/`data_entrega_real`), nunca pela data prevista.
- Registros antigos sem data real permanecem preservados e aparecem ao final do histórico.
- Nenhum banco novo e nenhum JSON operacional migrado.

## 20.4.9-I8.12.8-HF2 — Status Pronto + Resumo Operacional do Pedido
- Adicionado o status oficial **Pronto** entre Pago e Entregue; Pronto significa produção concluída aguardando retirada/entrega.
- Entregue passa a representar fechamento operacional e implica Pronto automaticamente, sem remover o registro do Histórico.
- Central/Fluxo e proposta oficial sincronizam Pronto de forma controlada; `producao_db` continua sendo somente etapa manual.
- Pedidos Prontos deixam de ser classificados como produção atrasada e saem da fila de liberação de consumo.
- Alpha Core, THU, Resumo Mensal, Central, Previsão e Produção passam a tratar Pronto pela mesma fonte oficial.
- Criado resumo compacto dos produtos do pedido, derivado dos itens da proposta, e propagado para cards/listas operacionais.
- Central diferencia **Top prioridades** da **Fila completa de produção**, evitando que pedidos aprovados pareçam ausentes do painel.
- Nenhum banco novo e nenhum JSON operacional migrado.

## 20.4.9-I8.12.7-HF1 — Comunicação coerente antes da liberação
- “Aguardando liberação” agora exibe **Material ainda não apurado**.
- Remove afirmações “Sem falta física” / “Materiais atendidos” quando ainda não houve consumo confirmado.
- Adiciona orientação única para confirmar a liberação e apurar disponibilidade.
- Mantém alertas de prazo sem criar status ou banco paralelo.

## 20.4.9-I8.12.7 — Previsão de Produção e Risco de Entrega
- Nova leitura derivada dos pedidos aprovados ainda não entregues, sem criar banco ou status paralelo.
- Classifica pedidos como Liberado para produção, Aguardando material, Compra em andamento, Aguardando liberação ou Risco de atraso.
- Quantidades já solicitadas ao fornecedor são alocadas FIFO entre pedidos do mesmo material para evitar falsa cobertura dupla.
- Risco considera data de entrega, material ainda indisponível e previsão de recebimento informada; não inventa tempo de fabricação.
- A mesma classificação aparece em Compras/Estoque, Central do Jorge, Histórico, Fluxo e componente operacional compartilhado com Anna.
- Nenhuma classificação altera automaticamente a etapa manual do Fluxo, o estoque, o planejamento de compras ou o preço de venda.

## 20.4.9-I8.12.6 — Planejamento de Compras por Necessidade
- Central separa falta real, quantidade já solicitada ao fornecedor e saldo ainda a solicitar.
- Solicitação ao fornecedor não movimenta estoque; somente recebimento registrado como compra/entrada regulariza pendências.
- Recebimentos parciais atualizam o planejamento e mantêm somente o saldo restante em aberto.
- Compras vinculadas a planejamento preservam rastreabilidade; exclusão reabre a quantidade e restauração recompõe o recebimento.
- Central do Jorge e status operacional dos pedidos comunicam compras em andamento usando a mesma fonte.
- Materiais com solicitação aberta não podem ser arquivados/consolidados até o recebimento ou cancelamento do saldo.

## 20.4.9-I8.12.4-HF4 — Materiais Inativos / Históricos
- Materiais consolidados passam a ser identificados explicitamente como Inativo/Histórico.
- Inativos deixam as listas operacionais sem perder histórico.
- Nova seção de consulta de materiais inativos e arquivamento seguro de cadastros sem uso.
- Arquivamento bloqueado quando há saldo, pendência ou vínculo ativo em Ficha Técnica.

## 20.4.9-I8.12.4-HF3 — Compras integradas à Ficha Técnica
- Entrada por compra passa a exigir destino de estoque explícito e prioriza o material definido na Ficha Técnica do produto relacionado.
- Nomes digitados na compra deixam de criar materiais duplicados silenciosamente.
- Quando houver vários materiais técnicos, o usuário escolhe qual foi comprado; unidade incompatível é bloqueada.
- Nova ferramenta de consolidação transfere saldo de duplicatas por movimentações auditadas, inativa a origem e preserva o histórico.
- Último custo do material oficial reconhece compras vinculadas e nomes antigos já consolidados.
- Entradas no material correto continuam quitando pendências de pedidos automaticamente, sem estoque negativo.

## 20.4.9-I8.12.4-HF2 — Fila oficial de liberação de consumo
- Fila usa exclusivamente Aprovado = SIM, Entregue = NÃO e consumo ainda não confirmado.
- Confirmação do consumo ou marcação de Entregue remove imediatamente a proposta da fila.
- Saneamento/Ficha Técnica deixam de filtrar a visibilidade: problemas ficam visíveis e bloqueiam apenas a confirmação.
- Central do Jorge passa a comunicar propostas aguardando liberação.

## 20.4.9-I8.12.3 — Ficha Técnica de Consumo
- Ficha técnica por produto do Catálogo Oficial, vinculada aos materiais controlados do estoque.
- Consumo por unidade, capacidade estimada e identificação de gargalo.
- Simulação de produção com saldo projetado, sem movimentação automática de estoque.
- Backup/restauração inclui fichas_tecnicas_db.json.

## 20.4.9-I8.11.2-HF1 — Auditoria dos Indicadores Mensais e Diários
- Conversão mensal corrigida para aprovadas ÷ todas as propostas emitidas da competência.
- Propostas encerradas/não fechadas permanecem no denominador da conversão.
- Resumo diário do Jorge diferencia movimentações registradas hoje da situação operacional atual.
- Auditoria sinaliza regularizações de status históricos feitas no dia.
- Situação operacional agora separa pedidos ativos, aprovação, produção, prontos, atrasados e carteira.
- Perfil Anna preservado sem alteração visual nesta etapa.

## 20.4.9-I8.11.2 — Resumo Mensal Executivo
- Novo bloco 📅 Resumo mensal no perfil Jorge, preservando o Resumo de hoje.
- Seletor de competência com propostas emitidas, total orçado, aprovadas, entregas, recebido, ticket médio e conversão.
- Integração com a Central de Faturamento Mensal: valor mensal em aberto e recebido por competência.
- Comparação automática com o mês anterior para os principais indicadores.
- Pedidos ativos, carteira aberta, aprovações pendentes e atrasados aparecem identificados como fotografia atual.
- Mantém Fonte Única de Status do HF3 e Radar de Atualizações do HF4; Anna não é alterada nesta versão.

## 20.4.9-I8.11.1-HF4
- Radar de Atualizações no Jorge com polling leve de eventos da Anna a cada 15s.
- Aviso de dados potencialmente desatualizados e botão de atualização manual do painel.
- Registro de eventos relevantes em propostas/status, catálogo/preço, cliente e Perfil Comercial.
- Indicadores permanecem sem atualização automática.

# 20.4.9-I8.11.1-HF3 — Fonte Única de Status
- Unifica a regra de status entre Anna, Jorge, THU, Alpha Core e indicadores.
- Mensalistas concluem operação com Aprovado + Entregue; pagamento individual não aparece como pendência.
- Atualizações de status usam leitura fresca e gravação condicional/retry para reduzir conflitos entre sessões.
- Auditoria registra o usuário real e o perfil Jorge recebe diagnóstico de sincronização.
- Nenhum JSON comercial alterado.

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

## 20.4.9-I8.11.2-HF2 — Unificação final de Atrasados
- THU, Alpha Core, Resumo Mensal e Central passam a consumir a mesma lista oficial de pedidos atrasados.
- Removida a regra paralela do THU que podia contar proposta encerrada como atraso.
- Prioridade executiva e alertas da Central passam a apontar exatamente os mesmos pedidos do Alpha Core.
- Hotfix somente de leitura; bancos comerciais e interface da Anna preservados.


## 20.4.9-I8.11.3 — Experiência de Digitação da Proposta
- Prévia em tempo de digitação no modal da Anna com total do item e novo total previsto da proposta.
- A prévia respeita preço especial por abatimento fixo em R$ do Perfil Comercial.
- Itens exibem quantidade × valor unitário = total do item.
- Novo campo `Evento` no cabeçalho da proposta, separado de Tema/Ocasião.
- Evento propagado para WhatsApp, HTML/PDF e Histórico.
- Edição e duplicação preservam Evento; propostas antigas continuam compatíveis.

## 20.4.9-I8.12.4 — Baixa de Estoque por Pedido + Pendências Automáticas
- Pedido aprovado não baixa estoque sozinho; Jorge revisa e confirma o consumo.
- Consumo usa Ficha Técnica, baixa somente o saldo disponível e nunca deixa estoque negativo.
- Falta de material vira pendência rastreável por pedido/material.
- Novas entradas regularizam automaticamente as pendências mais antigas (FIFO).
- Estoque, Central, Histórico, Fluxo e visão operacional da Anna passam a refletir o mesmo estado de materiais do pedido.
- Estorno do consumo é auditado e devolve ao estoque apenas as baixas ativas, preservando histórico.
- Pedido com consumo ativo não pode ser excluído antes do estorno.
- Mudança posterior no pedido/Ficha Técnica gera alerta de revisão antes da produção.

## 20.4.9-I8.12.4-HF1 — Saneamento integrado ao consumo por pedido
- Corrigida a resolução de itens de proposta com nomenclatura diferente do produto oficial.
- Nome oficial e aliases confirmados continuam com prioridade; o fallback de Saneamento só atua com correspondência forte e única.
- Categoria/subcategoria/variações podem apoiar a correlação sem duplicar produto nem alterar a proposta histórica.
- Consumo por pedido passa a localizar a Ficha Técnica pelo produto oficial saneado.
- THU e avisos operacionais deixam de apontar falsamente como “fora do Catálogo” itens resolvidos com segurança.
- Correlações automáticas ficam visíveis na comunicação operacional; aliases não são gravados automaticamente.
- Ambiguidades continuam bloqueadas para evitar baixa no produto errado.


## 20.4.9-I8.12.8-HF1 — Fonte Única Operacional da Central
- Aprovado, Pago e Entregue passam a ser lidos pela mesma fonte oficial em Central, I8.12.7, Alpha Core, THU e indicadores.
- Central e Fluxo sincronizam a produção com a mesma fotografia fresca do Histórico.
- `producao_db` permanece somente como etapa manual; não define mais condição comercial/operacional do pedido.
- Entrega marcada pela proposta espelha `Entregue` no Fluxo preservando a etapa anterior para eventual reabertura.
- Pedidos em Preparação/arte ficam visíveis na fila prioritária e no resumo da Central.
- Auditoria somente leitura permite comparar status oficial, materiais e etapa de produção por pedido.

## 20.4.9-I8.13.1 — Inteligência de Prioridades e Atrasos
- Prioridade operacional passa a ser calculada automaticamente por prazo, status oficial, produção/material e saída.
- Pedido Pronto nunca é classificado como atraso de produção; prazo vencido após Pronto vira `Saída atrasada`.
- Central Jorge ganha painel de prioridades com motivo e próxima ação.
- Fila completa de produção e Central de Entregas passam a exibir a mesma classificação derivada.
- Nenhum banco novo e nenhuma prioridade manual gravada na proposta.

## 20.4.9-I8.13.2 — Reserva de Estoque x Consumo Real
- Necessidade confirmada passa a reservar saldo livre sem movimentar o estoque físico.
- Baixa de estoque acontece somente quando a produção realmente começa; dados legados já baixados não são duplicados.
- Estoque exibe físico, reservado, disponível livre e falta real em pedidos.
- Entradas completam reservas FIFO; perdas/ajustes reconciliam excesso de reserva preservando pedidos mais antigos.
- Simulador e capacidade de Ficha Técnica deixam de contar material já comprometido com outros pedidos.
- Saída manual não pode consumir estoque reservado; consolidação de material com reserva ativa é bloqueada.
- Nenhum banco novo; `consumo_pedidos_db` guarda reservas e `estoque_db` continua guardando somente movimentos físicos.

## 20.4.9-I8.13.2-HF1 — Reconhecimento seguro de aliases na Reserva
- Corrige falso “sem correspondência no Catálogo Oficial” quando o item da proposta já existe como alias confirmado.
- Compatibilidade com aliases legados agrupados em uma única entrada separada por vírgulas/outros delimitadores.
- Nome oficial tem prioridade; alias só é aceito quando a correspondência é única.
- Reserva continua bloqueada em ambiguidade ou ausência de Ficha Técnica.
- Nenhuma alteração automática no Catálogo Oficial ou nos dados operacionais.

## 20.4.9-I8.13.2-HF2
- Ficha Técnica passou a ser opcional por pedido.
- Adicionados modos: Ficha padrão, materiais específicos do pedido e sem consumo de estoque controlado.
- Pedidos sem Ficha Técnica não ficam mais bloqueados apenas por essa ausência.
- Mantido vínculo seguro do Catálogo e fluxo Reserva → Consumo Real.


## 20.4.9-I8.13.2-CAT1-HF3 — Produto Comercial x Material de Estoque
- Materiais/insumos reconhecidos no Estoque deixam de exigir cadastro no Catálogo Oficial.
- Catálogo continua obrigatório apenas para itens comerciais sem vínculo seguro.
- Materiais listados no pedido não geram consumo duplicado; reserva segue Ficha Técnica ou decisão manual.
- Ambiguidade de nomes no Estoque continua bloqueada para não escolher material incorreto.

## 20.4.9-I8.13.2-CAT1-HF4
- Novo Orçamento: seleção pesquisável do Catálogo Oficial + digitação livre.
- Busca inclui aliases e salva o nome oficial quando há correspondência segura.
- Produto novo continua permitido sem cadastro prévio.

## 20.4.9-I8.13.2-CAT1-HF5
- Orçamento: produto do Catálogo Oficial passa a preencher preço, material e descrição automaticamente, mantendo edição livre no pedido.
- Catálogo: galeria de até 5 mídias por produto, com foto principal e opção de 1 vídeo.
- HTML/PDF: geração comercial passa a aproveitar múltiplas fotos; vídeo público pode ser acessado pelo catálogo/QR no PDF.

## 20.4.9-I8.13.2-CAT1-HF6
- Novo Orçamento (Jorge e Anna): cliente pesquisável por nome, WhatsApp, CPF/CNPJ e cidade.
- Seleção de cliente cadastrado preenche automaticamente identificação e preserva Perfil Comercial existente.
- Cliente novo continua livre e não exige cadastro prévio.
- Autopreenchimento só ocorre ao trocar a seleção, sem sobrescrever ajustes manuais da proposta.

## 20.4.9-I8.13.5-HF10 — Cliente novo pelo Orçamento
- Novo Orçamento completa o ciclo da HF9: cliente realmente novo é cadastrado no cadastro mestre ao salvar a proposta.
- Proposta recebe `relacionamento_id` do cliente criado, evitando herdar vínculo de cliente anterior em edições.
- Identificadores novos não fazem fallback silencioso por nome, protegendo clientes homônimos.
- Jorge e Anna usam a mesma regra; clientes existentes não são alterados automaticamente.

## 20.4.9-I8.13.5-HF11 — Confirmação visual do produto no Orçamento
- Novo Orçamento (Jorge e Anna) passa a mostrar a foto principal do produto selecionado no Catálogo antes de adicionar o item.
- Fotos adicionais ficam disponíveis em galeria recolhida; vídeo público pode ser aberto diretamente quando cadastrado.
- Produto sem mídia e produto livre continuam sem bloqueio.
- Prévia é somente leitura: preço oficial continua automático, enquanto Tema, Nome, Cor/Material, Idade/Data e Outros Detalhes permanecem manuais.
- `VERSAO` e `VERSAO.txt` alinhados em 20.4.9-I8.13.5-HF11.

## 20.4.9-I8.13.5-HF16 — THU • Agenda Executiva
- Central do Jorge ganha uma agenda única que consolida Retornos Comerciais, Cobranças Assistidas e prioridades operacionais de Produção/Entrega.
- A mesma proposta aparece uma única vez na agenda, mesmo quando possui mais de uma pendência; o sinal mais urgente vira a ação principal e os demais permanecem visíveis como contexto.
- A agenda organiza em Fazer agora, Resolver hoje e Acompanhar.
- Retornos/cobranças em estado “aguardar” e pedidos operacionais dentro do prazo não são transformados artificialmente em tarefa executiva.
- Atalhos de WhatsApp apenas preparam a mensagem; abrir o WhatsApp pela agenda não registra contato e não envia nada automaticamente.
- Os blocos específicos de Retornos e Cobranças continuam responsáveis pelo registro manual do contato real.
- O antigo cartão único “O que fazer agora” é substituído pela Agenda Executiva somente no perfil Jorge; Anna permanece com a experiência homologada anterior.
- Nenhum status, JSON, SQL ou banco novo foi criado.


## 20.4.9-I8.13.5-HF17 — Agenda Operacional Imprimível da Anna
- Central Operacional da Anna ganha uma agenda diária somente leitura com todas as propostas/pedidos ainda abertos.
- Cada linha mostra somente dados: número da proposta, status resumido, cliente, WhatsApp, produto(s) e data de entrega; nenhuma foto, mídia ou descrição visual é incluída.
- A lista é ordenada pela data de entrega mais urgente, com prazo vencido e entrega do dia destacados no status resumido.
- Dois PDFs A4 paisagem podem ser gerados: `Início do dia` e `Fechamento do dia`, ambos com data/hora da emissão para registrar a fotografia daquele momento.
- O PDF repete o cabeçalho da tabela em páginas adicionais e não embute imagens.
- A agenda é exclusivamente operacional: não altera proposta, status, contato, pagamento, produção ou entrega.
- Importação resiliente: uma atualização parcial do módulo da agenda não derruba o AlphaFest Manager; a Central continua disponível e informa a indisponibilidade da agenda.
- Nenhum JSON, SQL ou banco operacional foi alterado.

## 20.4.9-I8.13.5-HF18
- Agenda da Anna e alertas do Histórico alinhados à mesma Fonte Única de status.
- Recuperação segura de pedidos com marca comercial antiga de “não fechado” que depois avançaram para Pago/Pronto/Entregue.
- Status da agenda agora mostra marcos reais, sem inferir produção iniciada.
- Alertas históricos separam atraso de produção, atraso de saída e prazo vencido aguardando aprovação.


## 20.4.9-I8.13.5-HF23 — Catálogo 3D
- Biblioteca 3D do Jorge evolui para Catálogo 3D sem duplicar o acervo privado.
- Gerador permite selecionar modelos, conferir prévia responsiva e baixar HTML autocontido.
- Catálogo de cliente recebe somente nome, descrição, tempo de impressão e uma imagem.
- Arquivo 3D e metadados privados de armazenamento permanecem exclusivamente internos.

## 20.4.9-I8.13.5-HF24 — Continuidade na Agenda Executiva do THU
- O sinal `THU • Sem avanço registrado` passa a participar da ordem de decisão da Agenda Executiva do Jorge.
- Deduplicação preservada: o mesmo pedido aparece uma única vez mesmo quando possui continuidade + operação + cobrança/retorno.
- Urgência operacional concreta continua prevalecendo como ação principal; continuidade aparece como contexto secundário quando apropriado.
- Pedidos recorrentes no mesmo estágio podem entrar em Resolver hoje/Acompanhar mesmo antes de virarem atraso.
- Bloco detalhado da HF21 continua disponível como auditoria e usa o mesmo conjunto de sinais calculado para a Agenda Executiva.
- Nenhum envio, contato ou status é automatizado.
- Arquivos `VERSAO` e `VERSAO.txt` realinhados em HF24.

## 20.4.9-I8.13.5-HF25 — THU • Prevenção de prazo e pressão de agenda
- Agenda Executiva do Jorge passa a antecipar risco de prazo entre 3 e 10 dias antes da entrega.
- Radar cruza prazo de produção informado, dias úteis restantes, estágio/material e concentração de pedidos na mesma data.
- Concentração é tratada como pressão qualitativa de agenda; o Manager não inventa capacidade produtiva exata.
- Sinais preventivos entram na deduplicação da Agenda Executiva e nunca substituem uma urgência operacional concreta do mesmo pedido.
- Expander preventivo fica dentro da própria Agenda Executiva, evitando criar outro painel isolado.
- Nenhum status, contato, banco ou dado operacional é alterado automaticamente.
- Atualização parcial entre `app.py` e `thu_comercial_service.py` é tolerada sem derrubar a Central.


## 20.4.9-I8.13.5-HF26 — THU • Plano de amanhã
- Agenda Executiva do Jorge organiza preparação do próximo dia em Produção, Materiais e Saídas.
- Reaproveita prevenção da HF25 sem repetir atrasos/urgências de hoje.
- Pedidos Prontos com saída amanhã podem entrar como preparação logística.
- Nenhuma ação é executada automaticamente.

## 20.4.9-I8.13.5-HF27 — THU • Memória de tempo de ciclo observado
- Fluxo passa a registrar ciclos observados somente entre início explícito de produção e conclusão Pronto/Entregue.
- Tempo observado não é tratado como mão de obra nem capacidade exata.
- Quantidade do item é preservada em cada amostra.
- Timeline anterior pode ser aproveitada somente quando contém transições explícitas e coerentes.
- Central do Jorge ganha memória descritiva por produto com amostras, mediana, faixa observada e quantidade observada.
- Nenhum JSON/SQL novo e nenhuma transição automática criada para alimentar estatística.

## 20.4.9-I8.13.5-HF28 — Estorno visível de reserva/consumo
- Corrige a interface que escondia pedidos já reservados da seleção de estorno.
- Adiciona lista própria de reservas/consumos ativos no perfil Jorge.
- Reserva sem baixa física é apenas liberada; consumo real usa o estorno auditado do pedido.

## 20.4.9-I8.13.5-HF29 — THU • Identificação do ciclo em andamento
- Memória de tempo passa a mostrar qual proposta/produto compõe cada ciclo em andamento.
- Exibe cliente, quantidade, início explícito e usuário de início quando disponível.
- Adiciona botão para abrir o pedido sem alterar status ou criar eventos.
- Nenhum JSON/SQL operacional é modificado.

