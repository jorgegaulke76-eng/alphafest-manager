# Validação — AlphaFest Manager HF65.24.55

## Resultado da seleção crítica

Release cumulativa sobre a HF65.24.54. O gate do empacotador executa **289 testes em 28 arquivos**, todos aprovados, sem falhas, erros ou casos ignorados. Outros **6 testes de interface da HF53**, executados separadamente na árvore integrada, passaram. O diagnóstico compila **50 de 50 módulos críticos**.

| Grupo | Casos aprovados |
|---|---:|
| Carrinho com personalizações e ponte para a importação | 14 |
| Serviço de propostas semelhantes | 54 |
| Interface Streamlit da conferência | 18 |
| Integração real com leitores, permissões e salvamento | 24 |
| Navegação ao Histórico preservando rascunhos e seletores | 4 |
| Regressões críticas da base HF54 | 175 |
| **Total no gate do empacotador** | **289** |
| Interface de edição/abertura HF53, executada separadamente | 6 |

O inventário encontra 35 arquivos de teste; um arquivo depende de versão histórica e fica fora da seleção crítica. Inventário de arquivos não é contagem de testes executados. Os números finais e a assinatura dos fontes ficam no `UPDATE_MANIFEST.json` do ZIP.

## Carrinho e integração com a importação

`test_site_cart_personalizations_hf55.py` executa, por Node, os scripts realmente emitidos pela vitrine e pelo carrinho em um DOM funcional. A cobertura inclui migração de carrinhos antigos, manutenção da identidade após recarga, IDs repetidos ou inválidos, criação de outra personalização, edição/remoção por linha, eventos obsoletos, limite de 25 linhas e intervalo de 1 a 999 unidades.

Também verifica produtos com mesmo nome e IDs distintos, relacionados, teclado e link direto sem galeria, ausência de associação por nome quando falta identidade, recusa de slugs ambíguos produzidos pelo gerador real (Caneca A/Caneca Á), escaping de nomes/observações e a mensagem real gerada pela interface passando pelo parser HF54. Duas personalizações continuam sendo dois itens no rascunho do Manager.

Os testes anteriores de mensagens longas, cópia integral, métricas, busca, posts, PWA, geração da vitrine e importação continuam no gate aplicável. Nenhum teste anterior foi removido ou enfraquecido para acomodar esta implementação.

O teste HF54 de preservação da mensagem foi ajustado para localizar os dois payloads reais de persistência pelo campo `numero_proposta`. O snapshot novo da conferência também contém a mensagem, mas é somente leitura; a contagem de dois destinos de gravação e a verificação integral do texto foram mantidas.

## Propostas semelhantes

Os 54 casos de `test_proposal_duplicates_hf55.py` verificam documento, WhatsApp, normalização de DDI 55 e preservação de DDD 55, conflitos de identificação, homônimos, indício fraco por nome exato e ausência de identificação.

A comparação preserva quantidade e personalização por ocorrência, incluindo múltiplas linhas idênticas. Preço é ignorado na correspondência e incluído na assinatura da confirmação. A mensagem original deve ter o prefixo exato e conteúdo não vazio. São cobertos datas brasileiras/ISO, limites inclusivos da janela, registros futuros/sem data, cancelados/entregues, exclusão explícita de número, assinaturas estáveis e imutabilidade dos dados.

## Interface e integração com o aplicativo

Os 18 casos de `test_proposal_duplicate_ui_hf55.py` usam Streamlit AppTest e o serviço real. Cobrem consulta opcional, bloqueio inicial ao salvar, aceite explícito, nova leitura, alterações no rascunho/candidatos/situação, erro de leitura, tabela completa, navegação por callback, limpeza após sucesso e isolamento dos dois contextos. A confirmação sobrevive à remoção de widgets durante a navegação, mas não é reutilizada em uma nova geração de conferência.

O fixture usa ciclos distintos de `AppTest.run()` para redesenhar após o guard. Isso evita a limitação do AppTest 1.51 ao manter nós de selectbox removidos em um rerun na mesma sequência de mensagens. A UI não chama rerun nem grava propostas; o chamador real cuida desses passos.

Os 24 casos de `test_proposal_duplicate_integration_hf55.py` extraem os helpers e os corpos reais de Salvar do `app.py` por AST. Eles não iniciam o Manager completo. Serviços externos, navegação e persistência são substituídos por sentinelas para verificar:

- Consulta confirmada da chave `historico_orcamentos`, sem fallback online nem escrita.
- Falha de leitura e conteúdo inválido recusados, erro técnico mascarado e ausência confirmada aceita.
- Leitura local somente quando não há conexão configurada; arquivo ausente, válido e corrompido.
- Adapter HTTP real com resposta simulada, somente GET, sem importação ou gravação local.
- Permissão do Histórico respeitada na consulta, exibição e navegação.
- Snapshot independente de itens, metadados, preços, condições, origem e geração do formulário.
- Vínculo de cadastro explicitamente selecionado preservado quando compatível com os campos atuais, inclusive cadastro renomeado sem contato; dados de outro cliente não herdam o vínculo.
- Integração separada de Jorge e Anna; edição de registro existente fora do guard de criação.
- Interrupção dos dois corpos reais de Salvar antes de `garantir_cliente_orcamento` quando falta revisão; rascunho preservado.
- Uso do rerun de fragmento no diálogo da Anna e retorno à tela de orçamento no Jorge.
- Fluxo existente retomado somente quando a conferência libera a criação.

Os quatro AppTests de `test_proposal_duplicate_navigation_hf55.py` verificam a ida ao Histórico e a volta ao orçamento com os helpers reais, nos perfis de Jorge e Anna. Preservam o modo de cliente livre importado diante de homônimo cadastrado, o telefone revisado, os itens e os campos ainda pendentes de um produto escolhido do catálogo ou digitado livremente. O seletor do cliente também é mantido durante a navegação, evitando que a recriação do widget reaplique o cadastro homônimo.

Os seis testes adicionais da UI HF53 verificam a edição de itens e a abertura protegida dos rascunhos. O adaptador de rerun de fragmento já existente nesses testes continua restrito ao harness, pois o AppTest não fornece o identificador de fragmento de um navegador real.

## Conferência visual do site

Uma prévia interna foi gerada com catálogo e imagens fictícios, usando os geradores reais do site. A conferência em navegador verificou:

- Migração visual do carrinho de teste antigo com 25 linhas e aviso de limite.
- Criação de uma segunda personalização sem alterar a primeira.
- Duas canecas para Ana e uma para Pedro, com observações próprias.
- Mensagem de revisão com duas linhas, quantidades e textos completos.
- Recarga/nova abertura mantendo as duas personalizações.
- Layout de desktop e layout em quadro de 390 × 844 px, incluindo o aproveitamento da largura em linhas sem miniatura.

A largura de celular foi simulada em iframe; não houve teste em aparelho físico. A prévia não foi publicada. Nenhuma mensagem foi enviada pelo WhatsApp.

## Ambiente e pacote

Python 3.12.14, Streamlit 1.51.0 e Node 24.22.3. `requirements.txt` permanece igual à base HF54, e `DATA_VERSION` permanece 5.

O empacotador executa cada arquivo crítico em subprocesso isolado, bloqueia rede e importação de `app.py`, verifica a assinatura dos fontes e somente promove o ZIP temporário depois da auditoria. A revisão final verifica CRC, tamanho e SHA-256 de cada entrada, presença dos módulos obrigatórios, concordância de `VERSAO`, `VERSAO.txt`, `RELEASE_INFO.json` e manifesto, além da exclusão de dados operacionais, segredos, caches e compactados antigos. O template mestre HF7 mantém o hash congelado.

```sh
python build_update_package.py --output ALPHAFEST_MANAGER_HF65.24.55_PERSONALIZACOES_E_CONFERENCIA.zip --release-note UPDATE_INFO_HF65.24.55.md
```

## Limites

O Manager completo não foi iniciado no Streamlit Cloud e não houve acesso ao Supabase, WhatsApp ou Cloudflare de produção. A interface do Manager foi exercitada com AppTest e a integração foi verificada com código real extraído por AST; o salvamento em produção precisa da conferência operacional após a instalação.

A conferência de propostas não cria uma restrição de unicidade no banco, não garante a detecção de solicitações com dados ausentes ou conflitantes e não elimina a possibilidade de duas sessões gravarem simultaneamente. Os candidatos servem para a decisão do operador, incluindo novas encomendas legítimas do mesmo cliente.

As mudanças do carrinho exigem gerar e publicar o site pelo Manager atualizado. A instalação deste ZIP, sozinha, não altera o site público.
