# HF65.24.28 — Cabeçalho e rodapé unificados

- Página `/empresas/` reutiliza a estrutura real de cabeçalho, navegação e rodapé da página inicial.
- Navegação das subpáginas aponta corretamente para as seções da Home.
- Mantidos o formulário corporativo, fotos reais, kits e botão WhatsApp.
- Elimina logo redundante na faixa interna da página empresarial.
- Produção e publicação continuam manuais, sem alterar Secrets ou Supabase.

## Validação

- `python -m py_compile` dos serviços alterados.
- Geração de ZIP de publicação com `/empresas/index.html`.
- Renderização no Chromium para desktop e celular, sem overflow horizontal.
- Teste funcional do botão de orçamento abrindo wa.me com as informações preenchidas.

Gerado em: 2026-11-18T18:06:45-03:00
