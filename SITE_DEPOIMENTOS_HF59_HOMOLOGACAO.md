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
