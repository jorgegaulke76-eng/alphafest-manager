# AlphaFest HF65.24.58 RC4 - Relatorio de homologacao

Gerado em: 25/11/2026 14:30 (America/Sao_Paulo).

**SITUACAO: HOMOLOGACAO PARCIAL. NAO INSTALAR NO MANAGER EM PRODUCAO.**

## Base e alteracoes
- Origem: ALPHAFEST_MANAGER_HF65.24.58_HOMOLOGACAO_RC3.zip.
- Versao interna permanece: 20.4.9-I8.13.5-HF53.3-HF8-HF65.24.58.
- RC4 vincula a aprovacao a um marcador persistido das mutacoes das artes, impedindo reaproveitar um aceite ao arquivar e restaurar a mesma referencia.
- Ficha aprovada aponta para a ultima arte ativa mesmo que existam IDs duplicados.
- Caixa do Projeto testa a resposta de gravacao antes de informar sucesso ao salvar observacoes, arquivar ou vincular arquivos. Se o upload ocorreu mas o vinculo falhou, mostra aviso para conferencia.
- Copia profunda da Caixa do Projeto evita alterar objetos em cache antes da confirmacao da gravacao.
- O site publico, contratos de banco e aprovacao comercial nao foram alterados.

## Evidencias reais da execucao
- Arquivo especifico HF58: **16 testes aprovados**, sem erros ou ignorados.
- Suite selecionada (HF58 + rascunhos HF57 + roteiro HF51): **69 testes aprovados**.
- Descoberta geral unittest: **432 testes contabilizados, 4 erros de importacao e 93 ignorados** por ausencia de Streamlit. Resultado: REPROVADO.
- Execucao individual do conjunto critico (36 arquivos, isolamento por processo, max 18 s por arquivo): **27 arquivos aprovados**, 9 arquivos reprovados, **435 testes contabilizados**, 348 aprovados, 4 erros de importacao e 87 ignorados. Nao houve falha de assercao registrada. Resultado: REPROVADO.
- Diagnostico estatico release_diagnostics: aprovado antes da atualizacao das notas.
- A execucao sequencial oficial com timeout padrao nao concluiu no prazo deste ambiente, portanto NAO se atribui a ela um resultado de aprovacao.
- Streamlit nao esta instalado; a rede deste container nao resolve pypi.org. A tentativa de baixar a distribuicao por meio oficial nao concluiu. Nenhum substituto de Streamlit foi usado como prova de homologacao.

Arquivos criticos ainda bloqueados: test_proposal_draft_ui_hf57.py, test_proposal_draft_integration_hf57.py, test_proposal_review_ui_hf56.py, test_proposal_duplicate_ui_hf55.py, test_proposal_duplicate_integration_hf55.py, test_proposal_duplicate_navigation_hf55.py, test_site_quote_import_integration_hf54.py, test_site_quote_import_ui_hf54.py, test_site_integrity_hf53.py.

## Auditoria do pacote RC4
- Todos os caminhos sao relativos e inspecionados para evitar travessia de diretorio.
- Os arquivos do ZIP possuem SHA-256 no UPDATE_MANIFEST.json e o CRC deve ser verificado integralmente.
- A validacao do manifesto traz o estado HOMOLOGACAO_PARCIAL, deliberadamente diferente de OK. Nao usar este pacote no fluxo de atualizacao segura de producao.
- O pacote foi preparado sem bancos operacionais, credenciais, ambientes virtuais ou caches.

## Roteiro obrigatorio antes da liberacao
1. Extrair o ZIP em um diretorio novo, separado do repositorio que roda o Manager. Usar dados ficticios e nao conectar ao banco de producao.
2. Em Windows com Python, executar VALIDAR_HF58_WINDOWS.bat para instalar as dependencias em ambiente isolado, executar a regressao completa e o gate oficial. Guardar os logs.
3. Abrir o Streamlit de TESTE com Jorge e Anna; criar um pedido ficticio com dois itens e personalizacoes diferentes; gerar a ficha e conferir o texto completo.
4. Aprovar arte v1 e validar registro de usuario/data; depois adicionar v2, arquivar e restaurar uma arte e conferir a invalidez do aceite anterior e o checkbox desmarcado.
5. Simular conflito entre duas sessoes e erro de salvamento; a interface nao pode indicar sucesso sem persistencia real.
6. Conferir que gerar/baixar a ficha nao muda pedido, fluxo, financeiro ou estoque. Revisar protecao do arquivo TXT que contem dados internos.
7. Somente com esses resultados completos e aprovados, gerar e revisar um pacote FINAL separado por build_update_package.py. Nao promover automaticamente esta RC4.

## Limites conhecidos
- A assinatura compara metadados registrados, mais o marcador de mutacao gerenciado pelo Manager. Uma troca clandestina dos bytes em armazenamento remoto, sem alteracao de metadados ou do marcador, nao e identificavel por essa assinatura.
- A aprovacao de arte e registro manual operacional; nao substitui evidencia de aceite do cliente, aprovacao comercial nem liberacao de producao.
- O arquivo TXT inclui detalhes internos e nao deve ser enviado ao cliente sem revisao.

## RC5 - correções após execução real do GitHub Actions
- Em 25/11/2026, o primeiro job remoto instalou Streamlit 1.67.0 e executou 509 testes; identificou quatro erros.
- Compatibilidade Python 3.11: JSON-LD das páginas Dicas usa a variável `json_ld` fora da expressão de f-string.
- Importador do site: botão **Fechar revisão** é habilitado no mesmo rerun da análise, sem exigir interação adicional.
- Diagnóstico oficial passa a compilar também `site_dicas_multicanal_service.py`, impedindo regressão desse tipo.
- RC5 permanece **HOMOLOGACAO_PARCIAL** até regressão remota sem erros e conferência manual dos perfis. Não instalar em produção.
