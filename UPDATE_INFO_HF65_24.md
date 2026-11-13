# HF65.24 — Artes e vídeos finalizados

Base: HF65.23 YouTube OAuth.

- Editor de Dicas & Inspirações recebe JPG/PNG/WEBP; converte e limita arte a 320 KB no registro editorial, com imagem no artigo gerado após aprovação/publicação.
- Recebe MP4 já finalizado até 80 MB, mostra prévia e permite envio privado ao YouTube somente após OAuth e confirmação.
- Desativa botão de criação automática de Shorts; não transforma vídeos.
- Vídeo recebido fica na sessão Streamlit, não é armazenado permanentemente no Manager. Após envio, o ID é registrado no artigo. Para incorporar no site, confirmar manualmente que o vídeo tornou-se público e republicar site.
- Não altera módulos de pedidos, estoque, financeiro ou OAuth.
- Não publica site nem YouTube automaticamente.

## Instalação
Substitua o conteúdo do repositório com backup/commit anterior. Preserve Streamlit Secrets e dados da fonte única. Teste em homologação, após isso publique.
