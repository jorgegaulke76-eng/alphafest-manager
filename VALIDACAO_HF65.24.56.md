# Validação — AlphaFest Manager HF65.24.56

## Resultado da seleção crítica

Release cumulativa sobre a HF65.24.55. A seleção crítica contém **405 testes em 32 arquivos**, aprovados sem falhas, erros ou casos ignorados. Outros **6 testes de interface da HF53**, executados separadamente na árvore integrada, também passaram. O diagnóstico compila **52 de 52 módulos críticos**.

| Grupo | Casos aprovados |
|---|---:|
| Serviço de conferência final HF56 | 47 |
| Interface Streamlit da conferência final HF56 | 22 |
| Integração dos formulários e falha de persistência HF56 | 22 |
| Mensagem preservada e histórico do carrinho HF56 | 21 |
| Regressões HF55/HF54 e anteriores, incluindo quatro casos novos de assinatura inválida HF55 | 293 |
| **Total no gate do empacotador** | **405** |
| Interface de edição/abertura HF53, executada separadamente | 6 |

O inventário encontra **39 arquivos de teste**; um arquivo depende de versão histórica e fica fora da seleção crítica. Inventário de arquivos não é contagem de casos executados. O `UPDATE_MANIFEST.json` registra os resultados finais do gate e a assinatura dos fontes usados.

## Conferência comercial

Os 47 casos do serviço cobrem todos os bloqueios por linha e por proposta, avisos com e sem confirmação, independência do cálculo decimal, tolerância inclusiva de um centavo, datas brasileiras/ISO, edição histórica, imutabilidade de itens e metadados e assinatura estável do payload completo.

São exercitados preços/quantidades negativos, ausentes, não finitos e corrompidos, quantidades fracionárias legadas e textos com ponto decimal. A compatibilidade inclui strings com três casas decimais, como `2.000` e `18.500`, que o cálculo legado interpreta como 2 e 18,5. Agrupamentos mistos não são inferidos. Valores inválidos em uma linha impedem exibir subtotal parcial como total completo.

O aviso de total zero considera o valor calculado e o valor informado para salvar, evitando que a tolerância de um centavo permita um total gravado zerado sem confirmação. O serviço não reescreve preços, descontos ou condições.

Um caso compara 50 orçamentos válidos à função real `calcular_valores_proposta`, extraída por AST. Outro usa a importação HF54 real com personalizações independentes e preço ainda zerado. Esses cenários fazem parte dos 47 casos, não representam contagem adicional de testes.

## Interface e integração no Manager

Os 22 AppTests HF56 usam Streamlit e o serviço real. Verificam bloqueios visíveis, ausência de checkbox para ignorar erros, aceite para brindes e outros avisos, alterações depois da conferência, valores inválidos, recuperação após correção e estado separado entre Jorge e Anna.

A confirmação acompanha a assinatura completa da proposta e o contexto de data, edição e item pendente. Os testes cobrem personalização, preço, quantidade, condições, mensagem de origem, `_item_em_preenchimento` e número da proposta editada. Também exercitam ocultar/reabrir a interface, desmarcar o aceite, limpeza após sucesso e ausência de reaproveitamento de widgets antigos.

Os 22 testes de integração extraem os helpers e os corpos reais de salvar do `app.py` por AST, sem iniciar o Manager completo. A conferência e o estado de revisão são reais; banco, cadastro e navegação são substituídos por doubles. Os cenários comprovam:

- Conferência HF56 antes de HF55, cadastro de cliente e gravação, tanto em criação quanto em edição.
- Interrupção anterior a qualquer chamada de persistência quando existem bloqueios ou avisos não confirmados.
- Dados comerciais inválidos sem encaminhamento ao renderer de duplicidade HF55.
- Continuidade da revisão HF55 depois que os dados comerciais são liberados.
- Brinde confirmado mantendo preço zero, personalização, metadados e mensagem de origem.
- Mudança depois do aceite invalidando a autorização; aceite nunca ignora desconto excedente.
- Data vazia chegando como bloqueio, sem falha prematura em `strftime`.
- Item pendente limitado à geração atual e ao perfil correto; mudanças entre dois itens ainda pendentes invalidam o aceite.
- Rascunho e contextos de revisão copiados sem mutar a proposta nem persistir campos internos de conferência.
- Falha de gravação no Jorge mantendo itens, aceite e vínculos, sem anunciar sucesso ou agendar limpeza.
- Falha de gravação na Anna mantendo o diálogo, os itens e o aceite.
- Atualização do Jorge retornando a confirmação real da gravação e recusando registro ausente.
- Limpeza após sucesso restrita ao formulário que foi salvo.

O teste de integração HF55 recebeu somente um double para a nova conferência comercial anterior, mantendo suas verificações de duplicidade. A ordem e os resultados da conferência comercial são cobertos com a implementação real na suíte HF56.

### Assinaturas inválidas na conferência anterior

Os 18 AppTests originais da interface HF55 continuam aprovados. Quatro casos novos cobrem metadados NaN/bytes e prazo NaN, falha de assinatura após a criação do checkbox, validação com a seção oculta e recuperação com ou sem candidatos.

A falha invalida a revisão anterior e bloqueia o salvamento antes de consultar o Histórico, preservando os dados e mostrando uma mensagem legível. A correção dos dados permite uma nova consulta; nenhum campo é removido para tornar a assinatura válida.

## Carrinho e integração com a importação

Os 21 testes HF56 executam por Node o JavaScript realmente emitido pelo carrinho em um DOM funcional. Cobrem voltar/reabrir/recarregar sem perder a edição, persistência do texto vazio, assinatura de linhas/ordem/quantidade/nome/observações e bloqueio de envio de mensagem desatualizada.

Também verificam regeneração explícita, preservação e cópia integral do texto anterior, histórico de até dez textos manuais distintos, ausência de consumo do histórico por mensagens automáticas, descarte explícito, limpeza inclusive após remover o último item e recuperação de estado.

Os limites e erros de armazenamento são exercitados sem truncar o texto em memória. Há casos de formato/versão inválidos, quotas e indisponibilidade do armazenamento, mensagens extensas, conteúdo que exige escape, foco e acessibilidade. A mensagem real continua sendo aceita pelo parser HF54, preservando personalizações independentes.

As alterações nos testes anteriores do carrinho ficaram restritas às fixtures DOM, acrescentando os controles da nova interface. As assertivas anteriores foram mantidas. O contrato de `message()` executável isoladamente pela suíte HF54 foi preservado.

Uma revisão independente adicional executou três probes: falha apenas na chave dos itens, falha apenas na chave da revisão e mensagem manual de 100.016 caracteres. Nas falhas parciais, a divergência de assinatura impede enviar a revisão antiga como atual. O texto excedente permanece integral na sessão e na cópia, com aviso de que não pôde ser guardado. Esses probes não estão incluídos na contagem de 405 casos do gate.

## Conferência visual em navegador

A prévia interna usou os geradores reais da árvore integrada, dois produtos fictícios com imagens embutidas e um carrinho de teste criado na HF55. A conferência observou:

1. As duas personalizações existentes, com quantidades e observações independentes.
2. Um complemento manual preservado ao voltar aos itens e reabrir a revisão.
3. O mesmo texto recuperado depois de recarregar a página.
4. Mudança de quantidade de 2 para 3 tornando a mensagem anterior somente leitura e desativando o envio.
5. Regeneração explícita com a quantidade nova e preservação integral do complemento no histórico.
6. Cópia da revisão anterior conferida contra o texto integral na área de transferência.
7. Apresentação da revisão e do histórico em desktop e em quadro de **390 × 844 px**, com controles legíveis e acessíveis por rolagem.

A largura de celular foi simulada em iframe; não houve teste em aparelho físico. A prévia não foi publicada e nenhuma mensagem foi enviada pelo WhatsApp.

## Ambiente e pacote

Python **3.12.14**, Streamlit **1.51.0** e Node **24.22.3**. `requirements.txt` permanece igual à base HF55 e `DATA_VERSION` permanece **5**.

O empacotador executa cada arquivo crítico em subprocesso isolado, bloqueia rede e importação de `app.py`, verifica a assinatura dos fontes e somente promove o ZIP temporário depois da auditoria. Os módulos HF56 fazem parte da lista obrigatória do runtime e da compilação crítica.

A auditoria final verifica CRC, tamanho e SHA-256 de cada entrada, presença dos módulos obrigatórios, concordância de `VERSAO`, `VERSAO.txt`, `RELEASE_INFO.json` e manifesto e exclusão de dados operacionais, segredos, caches e compactados antigos. O template mestre HF7 mantém o hash congelado.

```sh
python build_update_package.py --output ALPHAFEST_MANAGER_HF65.24.56_REVISAO_FINAL_E_MENSAGEM_PRESERVADA.zip --release-note UPDATE_INFO_HF65.24.56.md
```

## Limites da verificação

O Manager completo não foi iniciado no Streamlit Cloud e não houve acesso ao Supabase, WhatsApp ou Cloudflare de produção. A interface do Manager foi exercitada com AppTest e a integração com os corpos reais de código extraídos por AST. A gravação em produção deve ser conferida operacionalmente após a instalação.

A revisão de valores não é uma transação de banco. A correção da confirmação de salvamento não implementa controle de edição concorrente nem uma transação entre cliente, proposta e vínculos. A conferência de propostas semelhantes mantém as limitações documentadas na HF55.

O aviso de item pendente usa os dados que chegaram à sessão. No formulário do Jorge, alterações ainda não enviadas por Adicionar Item podem existir somente no navegador. A revisão não promete recuperá-las. Rascunhos do Manager continuam sendo de sessão; as revisões do site continuam sendo do navegador, sujeitas à disponibilidade do armazenamento.

As mudanças do carrinho exigem gerar e publicar novamente o site pelo Manager atualizado. Instalar este ZIP, sozinho, não altera o site público.
