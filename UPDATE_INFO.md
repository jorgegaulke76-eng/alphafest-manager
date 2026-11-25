# HF65.24.53 — Melhorias operacionais (25/11/2026)

- Mensagem completa do orçamento do site, busca por tema, recuperação sem resultados e validade/paginação das ofertas.
- Publicação vinculada à prévia conferida, leitura online final e proteção de rascunhos em conflitos editoriais.
- Edição de itens, abertura assistida entre atendimento/projeto/orçamento e planejamentos na Central da Anna.
- Métricas por sessão e pacote condicionado a testes críticos executados.

Instalação: **LEIA_ME_ATUALIZACAO.txt**. Detalhes: **UPDATE_INFO_HF65.24.53.md**. Resultados e limites: **VALIDACAO_HF65.24.53.md**.

## Histórico

# HF65.23 — Conexão OAuth Google/YouTube (2026-11-13)

- Conectar canal oficial @AlphafestItatiba2026 com OAuth pelo próprio Streamlit.
- Confirmar conta Google e canal antes de salvar autorização.
- Guardar refresh token cifrado; upload apenas privado e mediante confirmação.
- Nenhuma publicação do site, vídeo ou mudança operacional automática.

# HF65.22 — Conteúdo multicanal para site e YouTube

- Nova seção **Dicas & Inspirações** no Manager, com 4 guias originais em RASCUNHO.
- Mesma fonte para texto do site, roteiro, descrição, URL e vídeo Short vertical sem áudio.
- Páginas estáticas por guia e lista /dicas/ geradas apenas após aprovação editorial.
- Novo arquivo de dados `site_dicas_multicanal_db.json`; não modifica outros bancos.
- Prévia e produção usam a mesma lista, e publicação continua exigindo o botão existente.
- Pacote de vídeo/roteiro e MP4 podem ser baixados para YouTube Studio.
- Envio direto por API é OPCIONAL, depende de OAuth no Streamlit Secrets e de clique explícito.
- Upload por API é sempre PRIVADO, com revisão antes de colocar público no canal.
- Não conecta o YouTube nem ativa vídeos ou artigos de forma automática sem autorização.
- AdSense, pedidos, estoque, financeiro, produtos e imagens seguem preservados.

## Atenção

Em produção, a conexão do YouTube requer configurar um cliente OAuth da Google Cloud
com escopo youtube.upload e um refresh_token autorizado pelo proprietário. Nunca
adicione senhas ou tokens ao GitHub nem ao cadastro de dicas. O primeiro teste deve
ser com vídeo PRIVADO.
