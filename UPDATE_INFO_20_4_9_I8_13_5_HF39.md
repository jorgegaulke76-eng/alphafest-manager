# AlphaFest Manager 20.4.9-I8.13.5-HF39

## Site paralelo / staging seguro

A HF39 transforma a vitrine homologada da HF38 em um pacote de staging separado,
sem alterar o site que já está no ar e sem modificar o domínio `alphafest.com.br`.

### O que entra
- nova área **🚧 Site paralelo / staging** na Central do Site;
- pacote ZIP estático gerado da mesma Fonte Única do Catálogo;
- `noindex` no HTML, `robots.txt` e `_headers` para homologação;
- checklist de virada do domínio com backup e rollback;
- preparação para homologação em endereço temporário `*.pages.dev` via Cloudflare Pages.

### O que NÃO acontece
- nenhum DNS é alterado;
- nenhum `CNAME` é incluído no pacote;
- `alphafest.com.br` não é apontado para a nova hospedagem;
- o site antigo não é desligado;
- nenhum produto, pedido, cliente ou documento operacional é modificado.

A troca do domínio só ocorrerá depois da homologação completa do novo site e de uma
etapa manual de virada, com possibilidade de rollback.
