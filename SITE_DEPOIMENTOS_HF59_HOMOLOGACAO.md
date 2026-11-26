# AlphaFest - Site: galeria de depoimentos com imagens originais

Escopo da issue #6. Alteração somente da apresentação pública gerada por site_home_content_service.py. Não altera banco, credenciais, textos cadastrados no Manager ou estado de publicação.

## Decisão visual aprovada
- Um título e um texto de agradecimento únicos, acima da galeria.
- Cartões de imagens exibem somente a imagem original, sem estrelas inventadas, sem legenda redundante e sem nomes abaixo da arte.
- Cards compactos e alinhados, imagens contidas sem recortar a mensagem.
- Clique/toque amplia a imagem em uma janela nativa, com botão de fechar, Escape e retorno do foco. A imagem base64 não é duplicada no HTML do cartão.
- Depoimentos textuais e vídeos permanecem disponíveis e exibem o conteúdo verdadeiro cadastrado.
- Continua respeitando ativo/inativo e a ordem recebida do Manager.

## Limitações e controle
Esta proposta é apenas uma implementação de revisão em branch própria; precisa de conferência visual com quatro depoimentos existentes em prévia desktop e mobile, seguida de teste do pacote de publicação. Não publicar ou fazer merge automaticamente.

## QA automático da página completa

O workflow da branch executa scripts/hf59_visual_qa.py, que chama a função real gerar_html_site_completo com quatro imagens FICTÍCIAS em proporções variadas (duas SVG, uma PNG raster e uma JPEG). O JPEG é gerado para o teste e não representa nenhuma mensagem real de cliente. Gera capturas de desktop (1440 × 900) e celular (390 × 844), incluindo o zoom. Verifica carregamento das quatro imagens e tamanho da seção. A partir do commit `f129508`, o teste percorre **cada uma das quatro imagens**, verificando correspondência entre cartão e ampliação, abertura, Escape, botão Fechar e retorno do foco em desktop e celular. A cobertura anterior com imagens fictícias foi aprovada na [execução #45823025832](https://github.com/jorgegaulke76-eng/alphafest-manager/actions/runs/45823025832), commit `8b2353e` (26/11/2026), incluindo QA de navegador desktop/celular e auditoria do ZIP fictício em memória.

As capturas e o HTML de teste ficam disponíveis no artifact AlphaFest-HF59-previa-ficticia da execução do GitHub Actions. Nenhum dado de clientes nem chave do Supabase é usado; nenhuma publicação é executada.

A inspeção visual com os quatro depoimentos REAIS cadastrados no Manager e o teste do ZIP do site público permanecem pendentes.

## Verificação do ZIP final

A automação executa também `scripts/hf59_zip_qa.py`, que monta em memória o ZIP **real** com `gerar_pacote_producao`, verifica CRC, HTML, índice, PWA, robots, política de cabeçalhos e arquivos esperados. Em seguida usa `extrair_pacote_publico` (mesmo filtro do envio Cloudflare) para conferir os assets e calcula o fingerprint. O teste não utiliza credenciais nem chama a API Cloudflare.

**Importante:** nenhum ZIP de produção com as quatro imagens fictícias é salvo para download. Só o relatório JSON de auditoria aparece nas evidências da CI. A publicação real depende de revisar as mensagens reais no Manager e de gerar o ZIP com os conteúdos verdadeiros, após liberação formal.

## Procedimento final — validação com depoimentos reais (SEM PUBLICAR)

**Pré-condição:** a interface utilizada para testar deve incorporar o commit aprovado `8b2353e` ou sucessor da branch `feature/site-depoimentos-imagens`. A instalação de produção (`main`) **não** contém necessariamente a mudança; abrir somente o Manager de produção não prova o layout novo. Não fazer merge para conseguir a prévia. Usar uma instância local/isolada e somente leitura dos dados existentes, quando disponível e autorizado.

### Conferência visual manual

- [ ] Confirmar a revisão/commit da prévia e a faixa de identificação de **prévia não publicada**.
- [ ] Registrar a quantidade de depoimentos **ativos** realmente existente, sem presumir que haja exatamente quatro. Selecionar quatro já cadastrados para amostragem se houver pelo menos quatro; não criar depoimentos fictícios no cadastro real.
- [ ] Conferir a fidelidade das quatro mensagens **dentro das próprias artes**, incluindo acentos, linhas, logotipos e bordas; não reescrever ou recortar a mensagem.
- [ ] Verificar o título e **um único** texto comum de agradecimento, sem descrição duplicada abaixo de imagem ou estrelas inventadas.
- [ ] Conferir imagens verticais e horizontais na largura desktop e celular: a miniatura pode ter margens para preservar proporções; a ampliação deve exibir toda a arte, com leitura possível.
- [ ] Abrir individualmente cada arte; testar Escape, botão Fechar, retorno do foco e ausência de rolagem horizontal indevida.
- [ ] Conferir que vídeos/depoimentos textuais, ordem dos registros e marcação ativo/inativo permanecem como foram cadastrados.
- [ ] Conferir o tamanho final do HTML/ZIP com **os dados reais** e anotar qualquer impacto antes de autorizar publicação. Não anexar imagens privadas dos clientes nem ZIP real aos artifacts públicos do GitHub.

### Gate de liberação

Registrar apenas resultado, commit, data e eventuais problemas (sem copiar mensagens privadas) no PR #7. Manter o PR em **draft** se qualquer item estiver pendente. Planejar backup e publicação em etapa separada da RC6/HF58, somente após autorização explícita. A aprovação automatizada com SVGs fictícios não substitui esta revisão real.

## Atualização de formatos — 26/11/2026

As quatro imagens reais do cadastro são JPEG e foram confirmadas como existentes no bucket catalogo, por leitura de metadados. Esta verificação **não** comprova que os arquivos abrem no navegador ou que o conteúdo é legível. O QA automatizado adicionou um JPEG gerado artificialmente; o commit `d152958` corrigiu o arquivo sintético após falhas de decodificação em Chromium. A execução mais recente deve ser conferida no GitHub Actions antes de marcar a cobertura JPEG como aprovada. Nenhuma imagem real foi copiada para artefatos públicos.

## Auditoria local e privada com JPEGs reais (sem credenciais)

A branch HF59 inclui `scripts/hf59_auditar_jpegs_local.py`, criado para execução **somente no computador autorizado**, com uma cópia local da branch e quatro arquivos JPEG já disponíveis no disco. Não usa URLs do Supabase, chaves de API, upload para GitHub ou Cloudflare, nem modifica o cadastro dos depoimentos.

Pré-requisitos: Python 3.11, dependências do Manager e Pillow instaladas no ambiente local. Os arquivos JPEG não devem ser adicionados à pasta versionada do GitHub nem anexados à CI.

Teste fictício, sem acesso a clientes:

```powershell
python scripts/hf59_auditar_jpegs_local.py --self-test
```

Auditoria local das quatro imagens, depois de disponibilizadas por meio autorizado:

```powershell
python scripts/hf59_auditar_jpegs_local.py "C:\\caminho\\01.jpg" "C:\\caminho\\02.jpg" "C:\\caminho\\03.jpg" "C:\\caminho\\04.jpg"
```

O teste confere decodificação JPEG, dimensões, inserção sem duplicação no HTML e integridade do ZIP gerado **somente em memória**, incluindo filtro de arquivos públicos da Cloudflare. Ele imprime apenas tamanho e dimensões; não publica os arquivos. **Não é uma conferência visual do conteúdo textual das artes, nem prova a identidade, ordem e estado dos registros reais do Manager.** A revisão humana da prévia da branch em desktop/celular e o ZIP final gerado a partir dos próprios cadastros continuam necessários antes da publicação.


## Integração da correção mobile — issue #8

A correção de rolagem horizontal da navegação/WhatsApp foi homologada na [execução #45855250641](https://github.com/jorgegaulke76-eng/alphafest-manager/actions/runs/45855250641) do [PR #9](https://github.com/jorgegaulke76-eng/alphafest-manager/pull/9). Em 26/11/2026, o PR #9 foi integrado **exclusivamente** à branch `feature/site-depoimentos-imagens`, commit de merge `42f2b124`. A branch `main` e a publicação permaneceram intactas.

Prévia privada integrada com os quatro JPEGs originais: `documentElement.scrollWidth` igual à largura da tela em 320, 390 e 430 px, bem como desktop 1440 px. Menu Mais e CTA WhatsApp dentro da viewport. As imagens reais não foram enviadas ao GitHub. O menu Mais foi aberto e fechado no ensaio local; os testes do PR #9 também passaram.

**Gate final:** confirmar CI do HEAD atualizado desta branch, conferir o ZIP definitivo gerado no Manager com o cadastro integral e aprovar a publicação em janela separada, com backup. A prévia local e o ZIP de teste, com dados parciais/fictícios fora dos depoimentos, não são pacote de produção.
