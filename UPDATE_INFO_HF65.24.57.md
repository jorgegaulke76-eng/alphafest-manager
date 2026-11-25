# AlphaFest Manager — HF65.24.57

## O que esta atualização entrega

Esta versão permite **baixar um rascunho de orçamento e retomá-lo em outra sessão ou computador**, tanto no Jorge quanto na Anna. O arquivo é preparado explicitamente, revisado antes da retomada e aberto pela proteção de rascunhos já existente.

O pacote é cumulativo sobre a HF65.24.56. Mantém a conferência final do orçamento, a conferência de propostas semelhantes, a importação da mensagem do site e as personalizações independentes do carrinho.

Versão completa: **20.4.9-I8.13.5-HF53.3-HF8-HF65.24.57**. A versão dos dados permanece **5**, com as mesmas dependências da HF56. Esta rodada atua no Manager e não exige republicação do site para utilizar os novos recursos.

## 1. Preparar e baixar o arquivo

No formulário do Jorge ou no diálogo de orçamento da Anna, abra **Baixar rascunho**, clique em **Preparar arquivo** e depois em **Baixar rascunho**. A área aparece também quando ainda não há itens. Um rascunho pode estar sem cliente ou sem data de entrega.

Preparar cria uma cópia dos dados recebidos pelo Manager naquele momento. A interface mostra o horário da preparação e a quantidade de linhas. O arquivo efetivamente baixado tem extensão `.json`; preparar, sozinho, não o coloca no computador.

Se o conteúdo recebido pelo Manager mudar depois da preparação, a cópia anterior deixa de ser oferecida para download. Prepare novamente para baixar os dados atuais. Uma mudança apenas do relógio ou da identificação da versão do Manager não altera a assinatura do conteúdo.

### Conteúdo preservado

| Informação | Comportamento no arquivo e na retomada |
|---|---|
| Cliente, documento, WhatsApp e evento | Preservados para revisão. |
| Itens já incluídos | Mantêm a ordem, as quantidades, os preços, as personalizações e os metadados compatíveis com JSON. |
| Desconto, entrega, prazo, modalidade, taxa e validade | Preservados, inclusive uma data ainda vazia. |
| Mensagem e observações de origem | Conservadas integralmente dentro dos limites do formato. |
| Número da proposta anterior | Referência informativa; a retomada abre um orçamento novo. |
| Atendimento e projeto anteriores | Referências informativas, sem vínculos ativos. |
| Informações de item ainda não adicionado | Guardadas como pendência manual quando já chegaram ao estado da sessão. |
| Edição de item ainda não aplicada | Guarda o item original e os últimos campos recebidos, para recuperação manual. |

Os preços do arquivo permanecem para conferência. A recuperação não consulta o catálogo para recalculá-los e não transforma pendências em itens automaticamente.

### O que precisa chegar ao Manager antes da captura

No Jorge, parte do novo item está em um formulário enviado pelo botão **Adicionar Item**. Nos dois perfis, o editor do item envia suas alterações ao usar **Aplicar alteração do item**. Texto digitado no navegador e ainda não enviado pode não estar disponível para captura.

Para incluir o item ou a edição na lista efetiva do orçamento, conclua essa ação antes de preparar o arquivo. As pendências oferecem recuperação do que já chegou ao Manager; não garantem recuperar texto existente apenas no navegador.

O download utiliza a cópia preparada sem reiniciar a página. Preparar e baixar não cadastram clientes nem salvam propostas.

## 2. Revisar e retomar

No **Jorge**, use **Novo Orçamento → Retomar rascunho**. Na **Anna**, use **Retomar rascunho** na **Central**; o resultado será aberto no diálogo de orçamento.

1. Selecione o arquivo de rascunho `.json`.
2. Confira cliente, contatos, linhas de itens, personalizações, quantidades, preços e condições.
3. Confira a origem e eventuais informações que exigem recuperação manual. A área **Conteúdo completo do arquivo** permite consultar também os metadados.
4. Marque **Conferi os dados deste arquivo para retomar o rascunho**.
5. Se o arquivo tiver número de proposta anterior, confirme adicionalmente que a retomada abrirá um orçamento novo.
6. Clique em **Retomar rascunho** e conclua a escolha de abertura, quando apresentada.

### Toda retomada abre um orçamento novo

**O arquivo não atualiza uma proposta existente.** Isso também vale quando foi preparado durante a edição de uma proposta salva. A revisão mostra o número de origem e exige um aceite específico para essa situação. Para continuar a edição do registro existente, abra a proposta pelo Histórico.

O novo rascunho não herda o número de edição, pagamentos, aprovação, entrega, histórico de eventos, permissões nem aceites das conferências HF55/HF56. Nenhum atendimento ou projeto é atualizado ao abrir o arquivo.

A identificação do cliente começa como digitação manual. Assim, um cadastro com nome igual não substitui automaticamente o telefone recebido no arquivo. O operador continua podendo selecionar explicitamente um cadastro existente.

### Quando já existe trabalho aberto

O Manager usa as escolhas da proteção HF53:

| Escolha | Resultado |
|---|---|
| **Continuar rascunho atual** | Mantém o trabalho atual e abre seu formulário. |
| **Substituir pelos novos dados** | Descarta o rascunho atual por escolha explícita e aplica o arquivo revisado. |
| **Cancelar abertura** | Cancela a solicitação e mantém o trabalho atual. |

As informações recuperadas de itens ainda não adicionados também contam como trabalho existente, mesmo que o formulário esteja sem cliente e sem itens. Guarde um arquivo antes de substituir um rascunho que ainda precise conservar.

Depois de cancelar, a revisão do arquivo continua disponível. Use **Reabrir revisão do arquivo** para conferir e solicitar novamente. Trocar ou remover o arquivo invalida os aceites anteriores. **Limpar revisão do arquivo** afeta apenas essa revisão, sem apagar o orçamento aberto.

### Conferência e salvamento continuam separados

A retomada exige permissão de visualizar e criar um orçamento, conferida ao solicitar e novamente ao aplicar a abertura. Se a autorização tiver sido retirada, o trabalho em andamento permanece.

Após recuperar, complete os campos necessários e use a conferência final da HF56. As regras comerciais continuam valendo: um arquivo pode guardar um item com quantidade zero ou preço negativo para que o trabalho não se perca, mas esse item continua bloqueando o salvamento até ser corrigido. As regras de confirmação de preço zero, condições pendentes e propostas semelhantes também continuam aplicáveis.

## 3. Recuperação manual de pendências

A seção **Informações recuperadas do rascunho** apresenta os itens não adicionados e as edições pendentes. Para cada edição, mostra o item original e os últimos campos recebidos. Essas informações não entram nos totais nem reativam o editor.

Recupere manualmente o conteúdo desejado. Quando terminar, marque **Confirmei a recuperação manual das informações acima** e use **Já recuperei estas informações**. A ação dispensa apenas as pendências informativas; os itens do orçamento e as referências de origem permanecem.

Ao exportar novamente antes dessa dispensa, as pendências recuperadas continuam no arquivo, junto das novas pendências recebidas. Só referências de conteúdo integralmente igual são deduplicadas. O limite não elimina entradas antigas silenciosamente.

### Depois de salvar a proposta

Se ainda houver informações de recuperação manual, o salvamento conserva um rascunho novo para concluí-las. Os itens já gravados saem da lista, evitando repeti-los; a identificação, as condições, as referências e as pendências permanecem disponíveis. Número de edição, vínculos ativos e editor anterior são limpos.

O Manager informa que a proposta foi salva e que as informações restantes continuam no rascunho. Na Anna, **Continuar** preserva esse contexto ao reabrir o diálogo. Uma nova exportação conserva as pendências e a lista atual, sem reincluir os itens já salvos.

Se não houver pendências manuais, o salvamento mantém a limpeza habitual. Uma falha de gravação mantém o rascunho conforme o fluxo da HF56.

## 4. Formato e limites

O arquivo usa o identificador `alphafest.rascunho_orcamento` e a versão de esquema **1**. O envelope contém versão do Manager, horário com fuso, origem, campos do formulário e listas de pendências.

| Limite | Valor |
|---|---:|
| Tamanho do arquivo UTF-8 | 2 MiB — 2.097.152 bytes |
| Itens já incluídos | 1.000 |
| Cada texto, incluindo nomes de campos | 100.000 caracteres |
| Profundidade da estrutura | 12 níveis, contando a raiz como 1 |
| Objetos, listas e valores | 40.000 nós; as chaves não somam nós |
| Pendências de item não adicionado | 50 |
| Pendências de edição | 50 |

Arquivos com esquema desconhecido, campos estruturais ausentes ou extras, codificação inválida, chaves duplicadas, valores não finitos ou tipos incompatíveis são recusados com mensagem. Também são recusados números que não podem ser representados pelos campos atuais e datas fora da faixa compatível com seus limites automáticos. Não há importação parcial ou truncamento.

Metadados desconhecidos dos itens são conservados quando pertencem ao formato JSON e respeitam os limites. A captura usa somente os campos previstos, sem exportar autenticação, configuração da sessão, cache ou permissões.

## Instalação

1. No Manager em uso, abra **Configurações → Núcleo Profissional → Atualização segura** e prepare/baixe o ponto de restauração.
2. Extraia o ZIP em uma pasta temporária.
3. Copie o **conteúdo** da pasta `alphafest-manager-main` para a pasta do repositório atual que contém `app.py`, substituindo os arquivos correspondentes. Preserve dados e configurações locais; não crie uma pasta adicional do mesmo nome dentro do repositório.
4. No GitHub Desktop, confira as alterações e faça Commit e Push no repositório e branch do aplicativo atual.
5. Aguarde o Streamlit atualizar e confira **HF65.24.57** na interface. Se necessário, reinicie pelo painel do Streamlit.

Não há SQL novo, migração de dados ou nova dependência. As melhorias desta rodada funcionam no Manager atualizado; não exigem gerar outro ZIP público do site.

### Conferência operacional após instalar

Use dados de teste identificados e confira:

1. Preparar e baixar um rascunho ainda sem itens.
2. Preparar outro com duas personalizações do mesmo produto e uma condição de entrega.
3. Alterar um campo e conferir que a interface pede uma nova preparação.
4. Selecionar o arquivo, revisar e retomar no Jorge e na Anna, conferindo os contatos e as linhas.
5. Com trabalho aberto, testar **Continuar** e **Cancelar** antes de usar **Substituir** em um rascunho descartável.
6. Abrir um arquivo cuja origem seja uma proposta existente e conferir o aviso de orçamento novo.
7. Conferir as informações de recuperação manual e baixar outro arquivo antes de dispensá-las.

Recuperar o arquivo não grava uma proposta. Use ambiente de homologação ou registros de teste identificados quando quiser conferir também o salvamento.

## Alcance desta entrega

O **arquivo baixado** é o meio de recuperação entre sessões. A versão não cria armazenamento automático de rascunhos no servidor nem sincronização entre computadores. Antes de fechar uma sessão com trabalho que deseja conservar, prepare e baixe o arquivo atualizado.

Esta entrega também não altera o mecanismo de edição simultânea do banco. A concorrência entre sessões precisa de uma evolução própria da persistência e permanece fora desta versão.

Novos módulos: `proposal_draft_service_hf57.py` e `proposal_draft_ui_hf57.py`. A integração está em `app.py` e `manager_workflow_hf53.py`. A validação detalhada está em **VALIDACAO_HF65.24.57.md**; o guia resumido está em **LEIA_ME_ATUALIZACAO.txt**. O manifesto registra a versão, os arquivos, seus hashes e o resultado do gate final.
