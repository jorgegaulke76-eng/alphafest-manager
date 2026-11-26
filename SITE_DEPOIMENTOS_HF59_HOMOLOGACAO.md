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

O workflow da branch executa scripts/hf59_visual_qa.py, que chama a função real gerar_html_site_completo com quatro imagens SVG FICTÍCIAS em proporções variadas. Gera capturas de desktop (1440 × 900) e celular (390 × 844), incluindo o zoom. Verifica abertura, Escape, botão de fechar, retorno do foco, carregamento das imagens e tamanho da seção.

As capturas e o HTML de teste ficam disponíveis no artifact AlphaFest-HF59-previa-ficticia da execução do GitHub Actions. Nenhum dado de clientes nem chave do Supabase é usado; nenhuma publicação é executada.

A inspeção visual com os quatro depoimentos REAIS cadastrados no Manager e o teste do ZIP do site público permanecem pendentes.

## Verificação do ZIP final

A automação executa também `scripts/hf59_zip_qa.py`, que monta em memória o ZIP **real** com `gerar_pacote_producao`, verifica CRC, HTML, índice, PWA, robots, política de cabeçalhos e arquivos esperados. Em seguida usa `extrair_pacote_publico` (mesmo filtro do envio Cloudflare) para conferir os assets e calcula o fingerprint. O teste não utiliza credenciais nem chama a API Cloudflare.

**Importante:** nenhum ZIP de produção com as quatro imagens fictícias é salvo para download. Só o relatório JSON de auditoria aparece nas evidências da CI. A publicação real depende de revisar as mensagens reais no Manager e de gerar o ZIP com os conteúdos verdadeiros, após liberação formal.
