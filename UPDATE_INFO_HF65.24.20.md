# HF65.24.20 — Páginas Novidades & Ofertas no Cloudflare

- Corrige a lista de arquivos aceitos no publicador Cloudflare, permitindo `novidades/index.html` e `novidades/pagina-N/index.html`.
- O arquivo gerado já continha as páginas do mural, mas elas eram descartadas antes do upload do Worker.
- Preserva os 43 posts, aprovação em lote, PWA, Dicas & Inspirações e WhatsApp.
- Não altera banco de dados nem publica automaticamente. Após instalar, gerar prévia e publicar pelo Manager.
- Inclui testes isolados de extração e paginação do arquivo público.
