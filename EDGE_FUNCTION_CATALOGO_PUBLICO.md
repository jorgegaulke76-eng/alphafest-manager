# LEGADO — NÃO É NECESSÁRIO NA I8.9.2

A I8.9.2 passou a usar GitHub Pages como camada pública de renderização. Este material permanece apenas para histórico da I8.9.1.

# I8.9.1 — Ativação única do link público de catálogo

O Supabase Storage força arquivos HTML públicos para `text/plain` por segurança. Por isso, abrir diretamente o objeto do Storage mostra o código-fonte do catálogo em vez da página renderizada.

A I8.9.1 inclui uma Edge Function pública e restrita somente à pasta `catalogos-publicos/` para servir esses mesmos arquivos como `text/html`.

## Arquivo da função

`supabase/functions/catalogo-publico/index.ts`

## Configuração de acesso público

`supabase/config.toml` já contém:

```toml
[functions.catalogo-publico]
verify_jwt = false
```

## Implantação por CLI

Na raiz do projeto, com Supabase CLI autenticado e projeto vinculado:

```bash
supabase functions deploy catalogo-publico --no-verify-jwt
```

## Implantação pelo Dashboard

Também é possível criar/deployar a função pelo editor de Edge Functions do Dashboard usando o conteúdo de `supabase/functions/catalogo-publico/index.ts`. A função precisa ficar pública, com verificação JWT desativada.

## Teste

Depois do deploy, abra:

`https://SEU-PROJETO.supabase.co/functions/v1/catalogo-publico?health=1`

A resposta esperada é `AlphaFest catalog renderer online`.

O AlphaFest Manager testa isso automaticamente. Quando a função estiver ativa, o botão **Publicar nova versão + QR** será habilitado e publicações antigas que possuem `object_path` também passarão a abrir pelo renderizador correto, sem precisar recriar o catálogo.
