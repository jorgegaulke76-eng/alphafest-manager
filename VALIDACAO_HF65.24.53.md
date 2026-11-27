# Validação — AlphaFest Manager HF65.24.53

## Resultado e escopo

A revisão foi executada sobre os fontes integrados da HF65.24.53, derivados da HF65.24.52. Passaram **115 casos críticos em 20 arquivos**, **6 testes de interface Streamlit** e **2 cenários adicionais dos formulários editoriais**. A compilação passou para **46 de 46 módulos críticos**.

Os testes usam dados sintéticos e substitutos locais para os serviços externos. Não foi iniciada a aplicação completa no Streamlit Cloud nem utilizados os bancos ou a publicação Cloudflare de produção. O ZIP é uma entrega para instalação; sua geração não instala a versão no ambiente existente.

## Seleção crítica executada pelo empacotador

| Arquivo | Casos aprovados |
|---|---:|
| test_manager_workflow_hf53.py | 18 |
| test_manager_operational_planning_hf53.py | 4 |
| test_planejamento_diario_hf49.py | 3 |
| test_planejamento_semanal_hf48.py | 2 |
| test_central_producao_painel_hf41.py | 4 |
| test_site_integrity_hf53.py | 15 |
| test_site_cart_hf53.py | 6 |
| test_site_search_hf53.py | 4 |
| test_site_posts_hf53.py | 7 |
| test_site_metrics_funnel_hf53.py | 8 |
| test_release_diagnostics_hf53.py | 8 |
| test_build_update_package_hf53.py | 7 |
| test_site_vitrine_hf52.py | 10 |
| test_site_release_cache_hf52.py | 3 |
| test_update_package_hf52.py | 1 |
| test_pwa_hf652414.py | 1 |
| test_posts_hf652417.py | 3 |
| test_posts_hf652418.py | 2 |
| test_roteiro_producao_hf51.py | 6 |
| test_hf652438_sob_encomenda.py | 3 |
| **Total** | **115** |

Resultado: zero falhas, zero erros, zero testes ignorados nessa seleção. Cada arquivo roda em subprocesso isolado, com rede e importação de `app.py` bloqueadas. Os testes da integração com o aplicativo extraem e executam os trechos necessários por AST; não iniciam o Manager completo.

O inventário encontra **27 arquivos de teste**; um depende de versão histórica (`test_hf652450_otimizacao.py`). Esse caso aparece como aviso de legado e fica fora da seleção crítica. Arquivos encontrados não são apresentados como se todos tivessem sido executados. O manifesto registra a execução crítica e a assinatura dos fontes.

Ambiente: Python 3.12.14, Streamlit 1.51.0 e Node 24.22.3 para executar o JavaScript emitido pelos geradores. As dependências de teste foram instaladas em ambiente local de QA; o pacote não altera `requirements.txt`.

## Interface e integração

Os seis casos de `test_manager_ui_hf53.py` exercitam os helpers reais do aplicativo com Streamlit AppTest. Cobrem os editores de itens, o estado do orçamento e a transferência protegida entre formulários. Todos passaram na árvore integrada.

Dois cenários adicionais exercitam o módulo real de Novidades e o formulário real de Dicas extraído por AST. Uma tentativa recusada no item A preserva os campos de A; selecionar B carrega a categoria, a situação e o vídeo próprios de B. Essa verificação levou à inclusão do item selecionado no identificador do formulário.

A revisão confirmou que o clique final de publicação lê os oito documentos por `load_document_confirmed`, que realiza somente GET, valida a resposta e distingue ausência confirmada de erro. Uma falha não consulta nem importa cópia local. O publicador só é chamado depois de a assinatura coincidir com a prévia.

Também foi conferido que cancelar a abertura de um formulário do Manager preserva a aprovação do site, e que recarregar a base editorial preserva o editor do orçamento e o rascunho recuperável. Os estados pertencem a áreas distintas da sessão.

## Conferência no navegador

A prévia foi gerada pelos serviços atualizados com 25 produtos sintéticos. As aberturas externas foram substituídas por indicação local, sem envio ou navegação real para WhatsApp.

- Busca por **Astronauta**: um produto correspondente ao tema.
- Busca sem resultado: contador zero, limpeza de filtros e ajuda contextual. Limpar recupera os 25 produtos.
- Orçamento curto: revisão e abertura no modo com texto preenchido.
- Orçamento longo: **25 itens e 13.126 caracteres**, incluindo o último produto, sem limite `maxlength` na revisão.
- Cópia da mensagem longa: área de transferência conferida, com 13.126 caracteres e o último produto presente.
- Abertura do orçamento longo: modo de conversa para colar, sem colocar o texto longo na URL.
- Oferta vencida em 24/11/2026: presente no HTML de teste, mas oculta na página em 25/11/2026.
- Novidades: Anterior da página 3 abre a página 2.
- Link `?produto=produto-de-teste-01`: abre a ficha correta.
- Quadro móvel de **390 × 844**: revisão completa e botões visíveis; painel do orçamento sem rolagem horizontal interna.

## Empacotamento e integridade

O caminho oficial utilizado é:

```sh
python build_update_package.py --output ALPHAFEST_MANAGER_HF65.24.53_MELHORIAS_OPERACIONAIS.zip --release-note UPDATE_INFO_HF65.24.53.md
```

O comando exige diagnóstico e execução crítica aprovados, gera o ZIP em área temporária, audita o conteúdo e só então promove o arquivo de saída. O `UPDATE_MANIFEST.json` é recriado com versão, tamanho e SHA-256 dos arquivos. Os novos módulos de integridade e de facilidades do Manager estão entre os arquivos obrigatórios.

A conferência final do artefato cobre CRC do ZIP, consistência de `VERSAO`, `VERSAO.txt`, `RELEASE_INFO.json` e manifesto, arquivos obrigatórios, correspondência dos hashes/tamanhos e exclusão de dados operacionais e segredos. O template mestre HF7 conserva seu hash de referência.

## Limites e conferência após instalar

AppTest não fornece o identificador real de fragmento do navegador. No teste da edição da Anna, um adaptador registra a solicitação de atualização do fragmento e a executa como atualização completa para verificar o estado. O diálogo real deve ser conferido no Streamlit instalado.

A conferência móvel usa um quadro com largura de celular, não aparelho físico. Confirma o painel de revisão do orçamento; não constitui homologação de responsividade de todas as páginas. A vitrine sintética de base ainda apresentou barra horizontal externa ao painel.

Conexão, permissões efetivas, publicação e dados reais dependem do ambiente instalado. Siga **LEIA_ME_ATUALIZACAO.txt**, confira HF65.24.53 e os fluxos principais antes de publicar o site. Não há migração de banco: `DATA_VERSION` continua 5.
