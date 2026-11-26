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

O workflow da branch executa scripts/hf59_visual_qa.py, que chama a função real gerar_html_site_completo com quatro imagens SVG FICTÍCIAS em proporções variadas. Gera capturas de desktop (1440 × 900) e celular (390 × 844), incluindo o zoom. Verifica carregamento das quatro imagens e tamanho da seção. A partir do commit `f129508`, o teste percorre **cada uma das quatro imagens**, verificando correspondência entre cartão e ampliação, abertura, Escape, botão Fechar e retorno do foco em desktop e celular. A cobertura ampliada foi aprovada na [execução #45823025832](https://github.com/jorgegaulke76-eng/alphafest-manager/actions/runs/45823025832), commit `8b2353e` (26/11/2026), incluindo QA de navegador desktop/celular e auditoria do ZIP fictício em memória.

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
