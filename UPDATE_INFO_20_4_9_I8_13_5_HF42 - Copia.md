# AlphaFest Manager 20.4.9-I8.13.5-HF42

## Site oficial — pacote final de produção

- Registra no Manager o estado atual da virada: zona Cloudflare Active, nameservers já migrados e domínio raiz `alphafest.com.br` conectado ao Worker `alphafest-novo`.
- Acrescenta o bloco **Produção oficial — HF42** na Central do Site.
- Gera `alphafest-site-producao-hf42.zip` para **New deployment** no mesmo Worker.
- O pacote final remove faixa de homologação e bloqueios `noindex` do staging.
- Acrescenta `robots.txt` liberado, `sitemap.xml`, canonical e metadados de indexação pública.
- Remove do HTML público notas internas sobre Manager/site legado; a Fonte Única permanece preservada internamente.
- Não altera DNS, nameservers, MX, webmail ou Custom Domains automaticamente.
- `www.alphafest.com.br` permanece pendente para validação separada após o deployment final do domínio raiz.
