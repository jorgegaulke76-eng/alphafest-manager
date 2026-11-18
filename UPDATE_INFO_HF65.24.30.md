# AlphaFest Manager HF65.24.30 — Inteligência Comercial

- Amplia métricas privadas existentes, sem nova tabela ou alteração de Secrets.
- Registra cliques nos botões de abertura do WhatsApp do carrinho e de Para Empresas, usando o evento `whatsapp_click` já autorizado.
- Exibe acessos por páginas e origem dos cliques; evita tratar cliques como vendas.
- Não registra o texto da mensagem nem dados pessoais inseridos nos formulários.
- Novas métricas exigem publicação do site no Cloudflare; dados não são retroativos.
- Preserva carrinho, catálogo, Galeria, Dicas, posts e páginas corporativas.
