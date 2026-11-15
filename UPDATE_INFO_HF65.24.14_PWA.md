# AlphaFest Manager HF65.24.14 — Site instalável (PWA)

- Manifesto Web App com logo oficial e identidade azul AlphaFest.
- Instalação nos navegadores compatíveis para Android, iPhone e Windows.
- Abre em janela própria, mantendo domínio, navegação e WhatsApp.
- Service worker seguro: não armazena páginas de produtos, mensagens, dados de clientes ou preços; mostra somente aviso de falta de conexão.
- Integração com empacotamento de produção e publicador Cloudflare (manifest.webmanifest, sw.js, offline.html).
- A instalação depende do navegador e do HTTPS após publicar o novo pacote pelo Manager.
- Sem publicação automática ou alteração de segredos, Supabase ou YouTube.
