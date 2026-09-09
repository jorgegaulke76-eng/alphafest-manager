# 20.4.9-I8.9.2.1 — Hotfix URL Supabase

Base exclusiva: 20.4.9-I8.9.2.

## Causa corrigida
O visualizador GitHub Pages usava `guejrwblcxptzlobhit.supabase.co`. A URL oficial do projeto AlphaFest é `guejrwlblcxptzlobhit.supabase.co` (havia um `l` ausente).

## Blindagem adicional
- O Manager passa a incluir a URL Supabase configurada em `SUPABASE_URL` no parâmetro público `base`.
- O GitHub Pages aceita apenas origem HTTPS no domínio `*.supabase.co`.
- O endereço oficial correto permanece como fallback para links antigos sem `base`.
- O `object_path` segue validado no padrão `catalogos-publicos/<catalogo>/<arquivo>.html`.

## Preservado
- Supabase Storage continua armazenando os HTMLs.
- GitHub Pages continua apenas como camada de renderização.
- QR Code, WhatsApp, PDF, validade de 30 dias, usuário responsável, Central, Modelos e Catálogo Oficial não mudam.
