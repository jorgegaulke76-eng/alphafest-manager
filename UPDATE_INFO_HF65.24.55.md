# AlphaFest Manager — HF65.24.55

## O que esta atualização entrega

Esta versão reúne duas melhorias no fluxo de orçamento: personalizações independentes no carrinho do site e conferência de propostas recentes antes de criar uma nova no Manager. O pacote é cumulativo sobre a HF65.24.54 e mantém a importação revisável da mensagem do site, a edição de itens e a proteção dos rascunhos das versões anteriores.

Versão completa: **20.4.9-I8.13.5-HF53.3-HF8-HF65.24.55**. A versão dos dados permanece **5**; não há SQL nem nova dependência de instalação.

## 1. Mesmo produto, personalizações separadas

No carrinho, cada linha passa a ter uma identidade própria. A ação **Outra personalização** cria uma nova linha do mesmo produto com quantidade 1 e observações vazias, logo abaixo da original. O foco vai para o campo de observações da nova linha.

Exemplo:

| Linha | Produto | Quantidade | Personalização |
|---|---|---:|---|
| 1 | Caneca Personalizada | 2 | Nome Ana, cor azul |
| 2 | Caneca Personalizada | 1 | Nome Pedro, cor verde |

Editar quantidade, escrever observações ou remover uma linha atua somente naquela personalização. As duas linhas permanecem separadas na mensagem do WhatsApp e na importação do Manager.

Ao abrir novamente a ficha de um produto já incluído e clicar em **Adicionar ao orçamento**, o site abre o carrinho e orienta a escolher a linha desejada. As quantidades existentes permanecem como estavam. Para aumentar unidades iguais, altere Quantidade; para mudar nome, cor ou tamanho, use Outra personalização.

O limite é de **25 linhas de itens/personalizações**, com **1 a 999 unidades por linha**. Valores fora desse intervalo ou fracionários são recusados, mantendo o valor anterior. O limite bloqueia novas linhas e informa o motivo.

A chave de armazenamento do carrinho foi preservada. As linhas antigas recebem identificadores próprios sem mesclar personalizações. Se um armazenamento antigo já contiver mais de 25 linhas, elas permanecem disponíveis e novas inclusões ficam bloqueadas até a redução. Não se trata de sincronização entre aparelhos: o carrinho continua pertencendo ao navegador.

A ficha identifica o produto pelo ID do cartão, inclusive na navegação por relacionados, teclado e link direto, sem depender da presença de uma galeria. Quando há identificações distintas, a ficha usa a identidade correspondente. Se o endereço interno do produto se repetir na vitrine (por exemplo, nomes que geram o mesmo slug), o carrinho recusa a inclusão ambígua e orienta o visitante a consultar pelo botão individual, sem escolher automaticamente outro cartão. Linhas sem miniatura utilizam toda a largura disponível.

A revisão da mensagem e a cópia integral de mensagens extensas foram mantidas. O site só abre o WhatsApp por ação do visitante; o envio da mensagem continua dependendo da confirmação na conversa.

## 2. Conferência de propostas semelhantes no Manager

O recurso aparece em propostas novas nos formulários de **Jorge e Anna**, depois dos itens e totais. É possível clicar em **Conferir propostas semelhantes** antes de salvar. O próprio botão normal de salvar também reconsulta o Histórico, mesmo que uma consulta anterior não tenha encontrado candidatos.

A consulta considera **a data de geração da proposta**, cobrindo hoje e os 29 dias anteriores. Precisa haver evidência de cliente em comum e pelo menos uma destas correspondências:

- A mesma mensagem original do site, integralmente preservada com o prefixo de origem usado pela importação.
- As mesmas linhas de produtos, quantidades e personalizações, incluindo a multiplicidade de linhas repetidas.

Documentos, WhatsApp ou vínculo de relacionamento podem fornecer evidência de identificação. O vínculo do cliente selecionado é aproveitado somente quando os campos atuais continuam compatíveis com esse cadastro, sem consultar ou gravar um novo cliente durante a conferência. A normalização de telefone considera o DDI brasileiro 55 quando aplicável, sem retirar indevidamente o DDD 55. Identificadores preenchidos e conflitantes impedem a correspondência. Quando só existe nome exato em comum, sem identificador comparável, o resultado é apresentado como **indício fraco**, exigindo a avaliação do operador. Não há busca aproximada por semelhança de nomes.

Os preços não decidem se os itens correspondem, pois a mesma solicitação pode ter sido recalculada. Entretanto, preço, quantidade, personalização, cliente, condições do formulário e contexto do rascunho fazem parte da confirmação: mudar esses dados exige uma nova conferência.

### Quando houver um possível registro anterior

1. Confira número, data, cliente, situação e motivos na tabela. Todos os candidatos encontrados são apresentados.
2. Use **Consultar no Histórico**, se necessário. A consulta não substitui o rascunho pelo registro anterior. A seleção do cliente e os campos pendentes também são preservados ao voltar, inclusive quando existe um cadastro com o mesmo nome e outro telefone.
3. Para retomar o rascunho na mesma sessão, volte a Novo Orçamento no Jorge ou abra Novo orçamento na Central da Anna.
4. Se for uma nova encomenda legítima, marque **Conferi as propostas relacionadas e quero criar uma nova**.
5. Use o botão normal **Salvar proposta**. O Histórico será consultado novamente antes de prosseguir.

Alterar um candidato relevante, sua situação ou os dados do rascunho invalida a confirmação anterior. A simples reordenação do Histórico ou a inclusão de uma proposta sem relação não exige novo aceite.

A conferência acontece antes de cadastrar o cliente ou gravar a nova proposta. Em caso de falha de leitura, o rascunho fica aberto e o salvamento aguarda uma consulta válida. A leitura online não importa contingência JSON local para o banco nem considera uma falha de rede como Histórico vazio. Em uma instalação explicitamente sem conexão configurada, a comparação usa o arquivo local disponível, em leitura somente.

### Alcance e limites

- A funcionalidade é uma conferência de **possíveis repetições**, não uma garantia universal contra duplicidades. Solicitações diferentes podem ser parecidas e pedidos recorrentes são permitidos mediante revisão.
- Propostas canceladas, encerradas e entregues também podem aparecer, com sua situação identificada.
- Registros sem data de geração válida, com data futura ou fora da janela ficam fora da comparação. A interface apresenta avisos para dados ausentes/inválidos e datas futuras.
- Contatos ou documentos conflitantes, identificadores incompletos e alterações de identificação podem impedir a correspondência de solicitações da mesma pessoa.
- O controle não é uma restrição de unicidade no banco e não bloqueia atomicamente duas sessões que gravem ao mesmo tempo.
- A edição de uma proposta existente conserva seu fluxo de atualização; a conferência é voltada à criação.
- Perfis sem acesso ao Histórico não recebem a tabela nem consultam seus dados por este recurso. A criação permitida para esses perfis mantém o fluxo existente, com indicação de que a conferência exige acesso ao Histórico.
- Nenhuma proposta é excluída, mesclada, cancelada ou alterada automaticamente por esta conferência. Os rascunhos e as confirmações pertencem à sessão.

## Instalação no Manager atual

1. No Manager em uso, abra **Configurações → Núcleo Profissional → Atualização segura** e prepare/baixe o ponto de restauração.
2. Extraia o ZIP desta atualização em uma pasta temporária.
3. Copie o **conteúdo** da pasta `alphafest-manager-main` para a pasta do repositório atual que contém `app.py`, substituindo os arquivos correspondentes. Preserve dados e configurações locais; não crie uma segunda pasta do mesmo nome dentro do repositório.
4. No GitHub Desktop, revise as alterações e faça Commit e Push no repositório e branch do aplicativo atual.
5. Aguarde a atualização do Streamlit e confirme **HF65.24.55** na interface. Se necessário, reinicie pelo painel do Streamlit.
6. Confira a abertura dos formulários de Jorge e Anna e a conferência de uma proposta nova. Use registros de teste identificados ou um ambiente de homologação para validar a gravação.

## Atualização do site público

**As novas personalizações só aparecem no site depois de gerar e publicar novamente o site pelo Manager atualizado.** A simples instalação do ZIP no Manager não troca o site público.

Na Central do Site, prepare uma nova prévia, confira Desktop/Celular e publique pelo fluxo habitual. No fluxo manual, gere o ZIP público em **Contingência / ZIP manual → Baixar ZIP de produção**. O ZIP entregue nesta atualização instala o Manager; o ZIP público é outro arquivo, gerado pelo próprio Manager.

Depois da publicação, confira no site:

- Um produto com duas personalizações, quantidades diferentes e observações próprias.
- Recarga da página mantendo as duas linhas.
- Remoção de uma linha preservando a outra.
- A mensagem de revisão com as duas personalizações completas.
- A importação dessa mensagem no Manager, mantendo duas linhas separadas.

## Arquivos e validação

Novos módulos: `proposal_duplicate_service_hf55.py` e `proposal_duplicate_ui_hf55.py`. O `app.py` integra os dois formulários; `site_carrinho_orcamento_service.py` e `site_vitrine_service.py` implementam o comportamento do site. Diagnóstico e empacotador incluem os módulos e testes novos.

O relatório detalhado está em **VALIDACAO_HF65.24.55.md**. O guia resumido está em **LEIA_ME_ATUALIZACAO.txt**. O manifesto do pacote registra arquivos, hashes, versão e resultado do gate.
