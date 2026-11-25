# AlphaFest Manager — HF65.24.56

## O que esta atualização entrega

Esta versão acrescenta uma **conferência final do orçamento** nos formulários de Jorge e Anna e preserva a **mensagem editada pelo cliente no carrinho do site**. Também corrige o caminho do Jorge que podia apresentar sucesso mesmo quando a gravação da proposta retornava falha.

O pacote é cumulativo sobre a HF65.24.55 e mantém as personalizações independentes do carrinho, a importação revisável da mensagem do site, a conferência de propostas semelhantes, a edição de itens e a proteção de rascunhos das versões anteriores.

Versão completa: **20.4.9-I8.13.5-HF53.3-HF8-HF65.24.56**. A versão dos dados permanece **5**. Não há SQL novo nem nova dependência de instalação.

## 1. Conferência final do orçamento

A seção **Conferência final do orçamento** aparece depois dos itens e totais, antes da conferência de propostas semelhantes e do botão normal de salvar. Funciona em propostas novas e na edição de propostas existentes, tanto no Jorge quanto na Anna.

A revisão apresenta cada produto e personalização em sua própria linha, com quantidade, preço unitário e total. O resumo reúne subtotal, desconto, taxa de entrega e total calculados de forma independente. A conferência não altera preços nem completa dados automaticamente.

### Correções obrigatórias

O salvamento aguarda correção quando a revisão encontra:

- Cliente, produto ou data de entrega ausentes/inválidos, ou lista de itens inválida/vazia.
- Quantidade não positiva ou inválida; preço, desconto ou taxa negativos; valores não finitos.
- Desconto maior que o subtotal dos itens. O total visualmente limitado a zero pelo formulário não libera esse caso.
- Divergência superior a **R$ 0,01** entre o subtotal/total informado e o cálculo independente.
- Modalidade diferente de Entrega ou Retirada, ou taxa incompatível com Retirada no snapshot conferido.

Os erros ficam visíveis fora da seção expansível. Não há confirmação que permita ignorá-los. Para corrigir um item já incluído, use **Editar**, aplique a alteração e confira novamente.

Quantidades positivas fracionárias já existentes continuam permitidas. Números em texto com um único ponto decimal conservam a interpretação do cálculo legado, inclusive três casas decimais; agrupamentos de milhar não são inferidos. O serviço não arredonda cada linha antes de somar.

### Pontos de atenção que permitem confirmação

Algumas situações podem ser legítimas e pedem decisão do operador:

| Situação | Comportamento |
|---|---|
| Item com preço zero | Confirmar que será oferecido sem cobrança ou corrigir o preço. |
| Total informado ou calculado zero | Confirmar a proposta sem cobrança. |
| Entrega no passado em proposta nova | Confirmar a data desejada ou ajustá-la. |
| Prazo de produção ou validade vazio, não inteiro ou não positivo | Corrigir ou confirmar a condição registrada. |
| Produto selecionado ou campos de item recebidos pelo Manager ainda não adicionados | Incluir o item antes de salvar ou confirmar que a proposta atual está correta. |
| WhatsApp vazio | Informação para atendimento presencial; não exige aceite. |

Quando houver pontos que exigem confirmação, marque **Revisei os pontos de atenção e quero salvar este orçamento** e use o botão normal de salvar. Um orçamento válido, sem esses pontos de atenção, não ganha uma etapa obrigatória de clique.

O aceite vale para os dados conferidos. Alterar cliente, itens, personalização, preço, condições, origem, item em preenchimento ou contexto da proposta exige nova revisão. Jorge e Anna mantêm confirmações independentes. A confirmação é preservada ao sair e voltar ao formulário na mesma sessão, se os dados continuarem iguais.

Em edição histórica, uma data de entrega passada, sozinha, não exige confirmação adicional. As demais verificações continuam ativas. Documento não se torna obrigatório por esta funcionalidade.

### Ordem do salvamento

Os dois formulários fazem primeiro a conferência HF56, depois a conferência HF55 aplicável de propostas semelhantes e somente então prosseguem para cadastro de cliente e gravação da proposta.

O aceite da importação de uma mensagem do site não substitui a conferência final. Por exemplo, um item aberto com preço zero na importação continua exigindo correção ou confirmação explícita antes de salvar.

A conferência HF55 mantém as regras anteriores de acesso ao Histórico e de criação de proposta nova. Ela também passa a apresentar um erro legível quando os dados do rascunho impedem a assinatura da conferência, em vez de interromper a tela. Corrigir os dados exige nova consulta e novo aceite, quando houver candidatos.

### Itens em preenchimento e rascunho

Somente os itens já incluídos na lista fazem parte da proposta salva. Use **Adicionar Item** para incluir um novo produto antes de salvar.

No Jorge, parte dos campos do item pertence a um formulário enviado ao clicar em Adicionar Item. Texto digitado no navegador e ainda não enviado pode não estar disponível para a conferência; o aviso não é uma recuperação automática desse texto. A revisão detecta o produto selecionado e os campos que já chegaram ao estado da sessão. Ela ignora campos de gerações antigas, evitando avisos sobre itens já adicionados.

Os rascunhos do Manager continuam pertencendo à sessão. A atualização não introduz salvamento automático de rascunhos entre aparelhos, fechamento de sessão ou reinício do servidor.

## 2. Mensagem editada preservada no carrinho

Ao abrir a revisão, o cliente pode completar o texto com nome, data desejada ou outras informações. Esse texto passa a ser preservado ao voltar aos produtos, reabrir a revisão e recarregar a página no mesmo navegador, enquanto os itens permanecem iguais. Apagar todo o texto é tratado como uma edição intencional; não faz a mensagem original reaparecer automaticamente.

### Quando os itens mudarem

Alterar quantidade, observação, produto, identidade/ordem das linhas, adicionar ou remover itens torna a revisão anterior desatualizada. O envio fica indisponível até usar **Gerar mensagem atualizada**.

A regeneração monta um texto correspondente ao carrinho atual. Se a versão anterior tinha edição manual, ela continua disponível para consultar e copiar; o cliente pode recuperar as informações desejadas para o texto atual. O site não tenta mesclar automaticamente comentários antigos com produtos que foram alterados ou removidos.

O histórico conserva até **10 textos manuais anteriores**, sem duplicatas de texto integral. Mensagens geradas que não receberam edição manual não consomem esse histórico. Ao atingir o limite, o cliente precisa descartar explicitamente uma versão que não deseja conservar antes de arquivar outra. A ação de limpar o carrinho também limpa a revisão e os textos anteriores.

### Armazenamento e limites

A revisão usa uma chave de armazenamento separada. O carrinho e a chave das versões anteriores continuam compatíveis, mantendo as linhas e suas personalizações.

Os textos pertencem ao navegador usado pelo cliente; não são sincronizados com outro aparelho. Se o navegador impedir o armazenamento ou o limite de recuperação for excedido, a interface informa que o texto precisa ser copiado antes de recarregar. O trabalho atual continua disponível em memória naquela página.

A recuperação valida o formato dos dados e limita cada texto a **100 mil caracteres**, com **2 milhões de caracteres** para o conteúdo serializado da revisão. Esses limites protegem a leitura de dados corrompidos; não significam truncar silenciosamente a mensagem em edição.

O fluxo de mensagens longas continua oferecendo cópia integral. O site somente abre o WhatsApp por ação do visitante, e o envio na conversa continua dependendo dele. As personalizações independentes da HF55 permanecem separadas na mensagem e na importação pelo Manager.

## 3. Falha de gravação no formulário do Jorge

O formulário passa a conferir o retorno real da gravação, tanto ao criar quanto ao atualizar uma proposta. Quando o salvamento não é confirmado, apresenta a falha e mantém o rascunho e as confirmações na sessão. Não prossegue para a mensagem de sucesso, limpeza do formulário ou atualização dos vínculos de atendimento/projeto daquele salvamento.

A edição relê o Histórico antes de localizar o registro e informa falha se ele não estiver disponível para atualização. A mudança não introduz uma transação entre cadastro de cliente, proposta e vínculos, nem resolve concorrência entre sessões; esses pontos continuam pertencendo ao fluxo de persistência existente.

## Instalação no Manager atual

1. No Manager em uso, abra **Configurações → Núcleo Profissional → Atualização segura** e prepare/baixe o ponto de restauração.
2. Extraia o ZIP desta atualização em uma pasta temporária.
3. Copie o **conteúdo** da pasta `alphafest-manager-main` para a pasta do repositório atual que contém `app.py`, substituindo os arquivos correspondentes. Preserve dados e configurações locais. Não crie uma segunda pasta do mesmo nome dentro do repositório.
4. No GitHub Desktop, revise as alterações e faça Commit e Push no repositório e branch do aplicativo atual.
5. Aguarde a atualização do Streamlit e confirme **HF65.24.56** na interface. Se necessário, reinicie pelo painel do Streamlit.
6. Confira a revisão final em Jorge e Anna. Para validar gravações, use registros de teste identificados ou um ambiente de homologação.

## Atualização do site público

**A preservação da mensagem do carrinho só aparece no site depois de gerar e publicar novamente o site pelo Manager atualizado.** A instalação deste ZIP no Manager não troca o site público.

Na Central do Site, prepare uma nova prévia, confira Desktop/Celular e publique pelo fluxo habitual. No fluxo manual, gere o ZIP público em **Contingência / ZIP manual → Baixar ZIP de produção**. O ZIP desta entrega instala o Manager; o ZIP público é gerado separadamente pelo Manager.

Depois da publicação, confira:

1. Adicionar duas personalizações do mesmo produto e abrir a revisão da mensagem.
2. Acrescentar uma informação manual, voltar e reabrir a revisão mantendo o texto.
3. Recarregar a página e conferir o texto preservado.
4. Alterar uma quantidade, gerar a mensagem atualizada e recuperar o complemento manual pelo texto anterior.
5. Importar a mensagem final no Manager e conferir itens, valores, condições e revisão final.

## Arquivos e validação

Novos módulos: `proposal_review_service_hf56.py` e `proposal_review_ui_hf56.py`. A integração usa `app.py` e `manager_workflow_hf53.py`. O carrinho está em `site_carrinho_orcamento_service.py`; o tratamento de dados inválidos da conferência anterior está em `proposal_duplicate_ui_hf55.py`.

Os detalhes da verificação estão em **VALIDACAO_HF65.24.56.md**. O guia resumido está em **LEIA_ME_ATUALIZACAO.txt**. O manifesto registra arquivos, hashes, versão e resultado do gate.
