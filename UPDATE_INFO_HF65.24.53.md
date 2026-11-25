# AlphaFest Manager — HF65.24.53 · Melhorias operacionais

**Versão:** 20.4.9-I8.13.5-HF53.3-HF8-HF65.24.53
**Data:** 25/11/2026 — America/Sao_Paulo
**Base de integração:** HF65.24.52.

Esta atualização reúne as correções prioritárias do site e as facilidades de uso do Manager definidas após a revisão. Inclui os ajustes da HF65.24.52 para a ficha de produto no celular e a abertura por link direto.

## Orçamento do site completo

A revisão preserva todos os itens e observações da mensagem. Foi removido o corte que limitava o texto a 6.000 caracteres.

Para mensagens curtas, o botão continua abrindo o WhatsApp com o texto preenchido. Quando a URL codificada ultrapassa o limite conservador adotado pelo site, a interface apresenta **Copiar mensagem completa** e **Abrir WhatsApp para colar**. O cliente copia o texto e o cola na conversa. O site não envia a mensagem sozinho.

Se o navegador não permitir copiar automaticamente, o texto fica selecionado e a interface orienta a cópia manual. O limite usado para escolher o modo de abertura é uma decisão de compatibilidade do site, não um limite universal declarado pelo WhatsApp.

## Busca, Novidades e ofertas

- A busca considera os temas cadastrados para os produtos.
- Sem resultados, o cliente pode limpar os filtros ou pedir ajuda pelo WhatsApp com o termo e a categoria pesquisados.
- O link **Anterior** de Novidades volta para a página correta, inclusive a partir da terceira página.
- Uma oferta com validade permanece disponível até o fim da data informada, no horário de São Paulo, e fica oculta a partir do dia seguinte.
- O navegador confere a validade ao abrir/retomar a página e periodicamente enquanto ela estiver aberta. A ação da oferta também confere sua validade.
- Uma página sem ofertas válidas apresenta uma orientação de continuidade.

A ocultação automática usa a validade já presente no site publicado. Alterar conteúdo, situação ou data no Manager exige nova publicação para levar os novos valores ao site. Ofertas sem data seguem sua situação editorial. Em navegador sem suporte à conferência de fuso, ofertas datadas ficam ocultas.

## Publicação vinculada à prévia conferida

Prévia e pacote público usam o mesmo conjunto de dados salvos: catálogo, galeria, empresa, campanha, conteúdo inicial, AdSense, Dicas e Novidades, além da versão e da data de publicação.

Quando esse conteúdo muda, a aprovação anterior perde a validade. No clique final para publicar, o Manager faz uma leitura online confirmada dos oito documentos e compara o resultado com a prévia. Uma diferença pede nova preparação e conferência; uma falha de leitura interrompe a publicação. Essa conferência final não usa uma cópia local como substituta de uma leitura online que falhou.

O botão usa a conexão Cloudflare existente. Atualizar o Manager não publica o site automaticamente.

## Conteúdos protegidos contra edição simultânea

Campanhas, conteúdo inicial, Dicas e Novidades guardam a base que originou o formulário. Uma atualização automática do cache não troca essa referência durante a edição.

Se outra sessão salvar antes, a tentativa seguinte não sobrescreve esse conteúdo silenciosamente. O Manager preserva a tentativa como rascunho recuperável, informa o conflito e oferece download. A área **Atualização dos conteúdos e rascunhos** permite recarregar a versão salva e recuperar a tentativa anterior.

Depois de recarregar, compare o rascunho com o conteúdo atual, reaplique o que deve permanecer e salve. A recuperação não mescla textos automaticamente. A troca entre duas publicações ou dicas carrega os campos do item selecionado, inclusive após uma tentativa recusada no item anterior.

Os rascunhos ficam na sessão. Baixe a recuperação antes de fechar ou reiniciar a sessão quando precisar conservar uma tentativa recusada.

## Edição de itens do orçamento

Jorge e Anna podem editar produto, quantidade, valor unitário e o texto completo de personalização de um item já adicionado.

- **Aplicar alteração do item** substitui o item na mesma posição.
- **Cancelar edição do item** mantém o item original.
- Mudar quantidade ou personalização preserva o preço combinado e os metadados existentes.
- Mudar explicitamente produto ou preço remove somente as marcações antigas que afirmariam que outra regra comercial calculou aquele preço.
- O editor recusa aplicar a alteração se o item tiver mudado desde sua abertura.

Durante a edição, é necessário aplicar ou cancelar antes de excluir itens, recalcular o perfil comercial ou salvar a proposta. O editor não recalcula silenciosamente o valor unitário. Os contextos de Jorge e Anna permanecem separados.

## Atalhos entre atendimento, projeto e orçamento

Os atalhos passam os dados diretamente ao formulário correspondente. Quando já existe um rascunho na sessão, aparecem três escolhas:

1. **Continuar rascunho atual:** abre o trabalho em andamento.
2. **Substituir pelos novos dados:** abre o novo trabalho após a escolha explícita.
3. **Cancelar abertura:** mantém a tela de origem.

Os dados são transferidos uma única vez e não são acrescentados novamente a cada atualização de tela. O vínculo de origem só é atualizado depois da abertura aceita. O projeto mantém seu contexto e seus campos na sessão.

A proteção conserva os dados que já chegaram à sessão do Manager. Texto ainda digitado apenas no navegador, dentro de um formulário não submetido, não constitui um salvamento automático.

## Planejamentos na Central da Anna

A Central da Anna mostra os planejamentos derivados do Histórico e do Fluxo:

- **Diário:** atrasados, hoje, amanhã, sem prazo, busca e abertura do pedido.
- **Semanal:** entregas previstas nas próximas sete datas e acesso ao pedido escolhido.
- **Downloads:** roteiro do dia em TXT e agenda da semana em CSV.

Essas novas áreas exibem dados operacionais, sem acrescentar valores comerciais ou telefones à projeção dos planejamentos. Os números representam pedidos, não horas nem capacidade de produção. A agenda oficial e os PDFs existentes continuam disponíveis.

## Métricas e qualidade da atualização

O indicador produto → WhatsApp considera uma visualização anterior ao clique, na mesma sessão e dentro da janela de análise, contando cada sessão uma vez. Contatos diretos continuam no total de cliques. Os indicadores não comprovam envio de mensagem, pedido ou venda.

O diagnóstico separa arquivos de teste encontrados, testes executados e testes aprovados. O empacotador oficial executa uma seleção explícita de regressões, inclusive testes antigos escritos como funções avulsas. Falha, ausência de teste, teste ignorado ou mudança dos fontes durante a validação impede a promoção do novo ZIP e preserva um arquivo de saída anterior.

## Instalação

1. No Manager atual, abra **Configurações → Núcleo Profissional → Atualização segura**, prepare a atualização e baixe o ponto de restauração.
2. Extraia o ZIP em uma pasta temporária.
3. Copie o **conteúdo** da pasta interna `alphafest-manager-main` para a pasta do repositório em uso, a que contém `app.py`. Substitua os arquivos correspondentes, mantendo os dados e configurações. Não apague o repositório nem crie uma segunda pasta do mesmo nome dentro dele.
4. Pelo GitHub Desktop, confira as alterações, faça **Commit** e **Push** no repositório/branch atual.
5. Aguarde o Streamlit e confira **HF65.24.53**. Se a sessão continuar na versão anterior, reinicie pelo painel do Streamlit e abra novamente.
6. Em um rascunho, confira editar/aplicar/cancelar um item. Confira os atalhos com rascunho existente. Na Central da Anna, confira os planejamentos e seus downloads.

Não há migração de banco nem SQL novo. `DATA_VERSION` permanece **5**. O pacote exclui dados operacionais, credenciais, segredos locais e arquivos compactados antigos. A preparação desta entrega usa dados sintéticos e não altera o ambiente instalado.

## Publicação do site após instalar

1. Abra a **Central do Site AlphaFest** e use **Preparar / atualizar prévia do site**.
2. Confira Desktop e Celular, busca por tema, ficha do produto, revisão do orçamento e Novidades/Ofertas.
3. Marque a confirmação e clique em **Publicar site agora**.
4. Se o conteúdo mudou, prepare e confira outra prévia. Se a leitura online falhar, tente novamente quando a conexão estiver disponível.
5. Abra o site no domínio habitual para conferir.

Para o fluxo manual, use **Contingência / ZIP manual → Baixar ZIP de produção** dentro do Manager atualizado. O ZIP desta entrega instala o Manager; ele não é o pacote estático do site para Cloudflare.

## Próximas etapas

Permanecem para outra atualização: importar a mensagem do site para o orçamento, separar personalizações diferentes do mesmo produto, revisar possíveis pedidos duplicados, controlar versões e aprovação de arte e ampliar o trabalho de galeria/imagens. Esta release entrega a base operacional e as correções acima.

Resultados e limites da verificação: **VALIDACAO_HF65.24.53.md**.
