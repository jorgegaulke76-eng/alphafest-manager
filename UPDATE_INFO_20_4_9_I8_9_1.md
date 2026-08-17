# 20.4.9-I8.9.1 — Correção do link público

Base exclusiva: 20.4.9-I8.9 testada.

## Causa identificada
O Supabase Storage serve arquivos HTML públicos como `text/plain` por decisão de segurança. Portanto, alterar apenas o `Content-Type` do upload não resolve o problema de renderização no navegador.

## Correção
- HTML continua armazenado como artefato imutável no bucket `catalogo`.
- Link do cliente passa a usar `functions/v1/catalogo-publico?path=...`.
- A Edge Function busca somente caminhos válidos em `catalogos-publicos/` e devolve a resposta como `text/html; charset=utf-8`.
- QR Code e WhatsApp usam a URL renderizada.
- PDF inclui a URL renderizada quando o serviço estiver ativo.
- Publicações antigas são compatíveis porque o sistema deriva a nova URL a partir do `object_path` já salvo.

## Ativação única
Implantar a Edge Function incluída em `supabase/functions/catalogo-publico/index.ts` com verificação JWT desativada. O arquivo `supabase/config.toml` já traz `verify_jwt = false`.

## Segurança
A função não é um proxy aberto: ela rejeita qualquer caminho fora do padrão `catalogos-publicos/<catalogo>/<arquivo>.html`.
