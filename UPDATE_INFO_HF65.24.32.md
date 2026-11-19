# HF65.24.32 — Correção de métricas comerciais

- Corrige envio tardio dos eventos `whatsapp_click` de `carrinho` e `empresas`: o POST começa antes de abrir o WhatsApp, sem esperar a consulta geográfica.
- Torna a consulta de localização opcional e não bloqueante; a primeira visualização pode não registrar cidade, mas preserva as demais dimensões.
- Evita inserir duas vezes o rastreador na mesma página.
- Mantém dados, credenciais, telas e publicação do Cloudflare existentes.
- O clique registra intenção de abrir o WhatsApp; não confirma mensagem enviada nem venda.
- **Validação necessária em produção:** atualizar a prévia, publicar, visitar `/empresas/` e conferir `page_view`; acionar o orçamento do carrinho e o corporativo e conferir o contexto dos novos eventos em métricas privadas.
