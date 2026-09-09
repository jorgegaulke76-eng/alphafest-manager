# 20.4.9-I8.9.2 — Link Público via GitHub Pages

Base exclusiva: 20.4.9-I8.9.1.

## Objetivo
Corrigir definitivamente a abertura do catálogo público no navegador sem alterar a persistência dos catálogos no Supabase.

## Arquitetura homologada
- Supabase Storage continua armazenando o HTML imutável em `catalogos-publicos/...`.
- GitHub Pages `https://jorgegaulke76-eng.github.io/alphafest-catalogos/` é a camada de apresentação ao cliente.
- O link público usa `?path=<object_path>` e o visualizador busca o HTML público no Supabase.
- QR Code, WhatsApp, PDF e botão “Abrir catálogo” usam o mesmo link GitHub Pages.

## Compatibilidade
- Publicações antigas não precisam ser refeitas quando possuem `object_path`: a Central reconstrói automaticamente a URL I8.9.2.
- `storage_url` continua apenas como referência técnica; não é enviado ao cliente.
- Edge Function `catalogo-publico` deixa de ser requisito e permanece apenas como legado da I8.9.1.

## Segurança e governança
- O gerador de URL aceita apenas caminhos `catalogos-publicos/<catalogo>/<arquivo>.html`.
- Catálogo Oficial permanece como única fonte de produtos e preços.
- Validade de 30 dias, responsável, histórico e rastreabilidade foram preservados.
- O endereço do visualizador pode ser substituído por `CATALOG_VIEWER_URL` em `st.secrets` ou variável de ambiente sem novo ajuste de código.
