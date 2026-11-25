# AlphaFest Manager — HF65.24.54 · Importação do orçamento do site

**Versão:** 20.4.9-I8.13.5-HF53.3-HF8-HF65.24.54

**Data:** 25/11/2026 — America/Sao_Paulo

**Base:** HF65.24.53. Pacote cumulativo com as melhorias das versões .52 e .53.

## O que esta atualização entrega

A mensagem enviada pelo cliente a partir do carrinho do site pode ser colada no Manager, analisada e aberta como rascunho no formulário normal de orçamento. O recurso está em **Novo Orçamento** para Jorge e na **Central Operacional** para Anna, em **Importar orçamento do site**.

O fluxo reutiliza o editor de itens e a proteção de rascunhos da HF65.24.53. Não é necessária uma integração com a conta do WhatsApp: a mensagem é copiada e colada pelo operador.

## Análise e revisão

O importador reconhece a estrutura numerada que o site já gera:

```text
1. Caneca personalizada
Quantidade: 2
Personalização/observações: Tema espaço, nome Ana

2. Topo de bolo
Quantidade: 1
Personalização/observações: Pedro, 7 anos
```

A introdução e o encerramento padrão são aceitos. Mensagens longas e observações em várias linhas são preservadas. Cada produto identificado aparece em uma linha própria de revisão, com quantidade, valor unitário e personalização editáveis.

Produtos repetidos permanecem separados quando vierem em linhas distintas na mensagem, conservando suas personalizações. Esta versão não altera a forma de agrupamento de produtos no carrinho público.

Quantidade ausente ou inválida precisa ser informada pelo operador; o importador não transforma silenciosamente um campo ausente em uma unidade. Problemas estruturais, como numeração repetida ou interrompida, pedem correção da mensagem e nova análise. Listas numeradas dentro das observações são sinalizadas para conferência.

A mensagem original permanece integral na origem do rascunho, inclusive texto adicional sobre prazo, entrega ou condições. Esse texto não é interpretado como cadastro de cliente, preço ou compromisso confirmado. O nome, WhatsApp e evento podem ser informados na revisão; a data e as demais condições são conferidas no formulário normal.

Há limites explícitos de 100.000 caracteres e 100 itens por análise. Uma solicitação acima desses limites é recusada com orientação para divisão, sem cortar os dados silenciosamente.

## Catálogo e preços

A correspondência usa nome ou alias exato normalizado e exige um único produto ativo. Não há escolha aproximada de produto.

- Correspondência única: sugere o nome oficial e o preço atual do catálogo.
- Nome desconhecido, ambíguo ou inativo: mantém o produto como texto livre e informa a pendência.
- Preço ausente ou inválido: apresenta valor zero para revisão, sem inventar preço.

Os preços sugeridos podem ser ajustados antes da abertura. Um item com valor zero exige uma confirmação específica. O Perfil Comercial do cliente não recalcula automaticamente os itens importados; seu botão habitual continua disponível no orçamento após a identificação do cliente.

O catálogo é consultado online por leitura confirmada, sem importar dados locais para o banco. Antes de abrir o rascunho, uma nova consulta verifica se os dados usados para correspondência e preços mudaram. Se mudaram, o Manager pede nova análise. Alterações de fotos ou ordenação, sem alteração comercial relevante, não invalidam a revisão.

Se a conexão falhar, a mensagem e a revisão são preservadas para outra tentativa. A importação não trata uma cópia local antiga como confirmação do catálogo atual.

## Proteção do rascunho e da identificação

**Abrir rascunho no orçamento** enfileira uma única abertura. O fluxo não reaplica os itens automaticamente a cada atualização de tela.

Se houver outro trabalho em andamento, aparecem as escolhas da HF65.24.53: continuar o rascunho atual, substituir pelos novos dados ou cancelar a abertura. A importação conserva sua revisão e oferece **Revisar importação novamente** para retomá-la após essa escolha.

Os dados de cliente revisados começam no modo **Cliente novo / digitar manualmente**. Isso evita substituir um WhatsApp novo por outro cadastro com nome semelhante. O seletor de clientes existentes permanece disponível para escolha explícita. Enquanto o formulário pertence à importação, a identificação comercial usa a regra que protege contra nomes iguais com telefone conflitante.

A mensagem de origem é apresentada em uma área recolhível, evitando que um texto extenso ocupe o topo inteiro do orçamento. Ao salvar a proposta pelo fluxo normal, esse conteúdo é mantido em `briefing_origem`, que já existe no sistema.

## O que acontece somente após a revisão normal

Analisar e abrir o rascunho não cria uma proposta nem um cadastro de cliente, não aprova pedido e não envia WhatsApp. O salvamento segue o botão normal de orçamento. Identificação, preços, prazo e entrega devem ser conferidos antes desse salvamento.

A revisão permanece na sessão do navegador/Manager. Para manter o trabalho após fechar ou reiniciar a sessão, conclua o salvamento da proposta pelo fluxo habitual.

## Instalação

1. Prepare e baixe o ponto de restauração em **Configurações → Núcleo Profissional → Atualização segura**.
2. Extraia o ZIP em uma pasta temporária.
3. Copie o conteúdo de `alphafest-manager-main` para a pasta do repositório atual que já contém `app.py`, substituindo os arquivos correspondentes e mantendo os dados/configurações. Não apague o repositório nem crie uma pasta duplicada dentro dele.
4. Faça **Commit + Push** no GitHub Desktop, no mesmo repositório/branch do aplicativo.
5. Aguarde o Streamlit e confirme **HF65.24.54**. Reinicie pelo painel do Streamlit se necessário.
6. Confira a importação com uma mensagem de exemplo, a revisão, a proteção de rascunho e a abertura nos dois perfis utilizados.

Não há SQL novo, migração de banco ou alteração em `requirements.txt`. `DATA_VERSION` continua **5**. O pacote exclui dados operacionais e segredos locais.

## Site e continuidade

A importação aceita o formato de mensagem do carrinho já existente, portanto não exige republicar o site para funcionar. Se as correções públicas da HF65.24.53 ainda não foram publicadas, elas estão incluídas neste pacote: após instalar, prepare/confira uma nova prévia e publique pela Central do Site.

O ZIP desta entrega instala o Manager. Para o fluxo manual de Cloudflare, gere o pacote público na Central do Site do Manager atualizado.

Próximas frentes: personalizações independentes no próprio carrinho público, revisão de possíveis propostas duplicadas e controle de versões/aprovação de arte. A importação desta versão não é um detector de duplicidade de propostas já salvas.

Os resultados e limites dos testes estão em **VALIDACAO_HF65.24.54.md**.
