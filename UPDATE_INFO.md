# AlphaFest Manager — HF53.3-HF8-HF61

## Catálogo — marcação rápida de categorias extras do site

Atualização incremental sobre a HF60. Mantém a lógica de multicategorias da HF59 e acrescenta uma forma mais rápida de trabalhar direto na grade de Produtos.

### Entregas
- nova seção **Categorias extras do site · marcação rápida** na aba Produtos;
- escolha uma categoria-alvo e marque/desmarque produtos por checkbox, no mesmo padrão da edição rápida já usada para Publicar/Preço/Destaque/Carrossel;
- filtro por nome/categoria/subcategoria e opção **Só produtos do site**;
- produtos cuja categoria principal já é a categoria-alvo não aparecem na grade, porque já pertencem a ela automaticamente;
- auto-save em `CategoriasExtrasSite`, sem duplicar produto e sem mudar categoria principal;
- contadores, cartões **Explore por categoria** e filtros do site continuam usando a mesma lógica de multicategorias já homologada;
- nenhuma publicação automática: o site só muda pelo fluxo seguro de publicação assistida.

### Preservado
- HF60 — correção de conexão/publicação Cloudflare;
- HF59 — site simplificado e multicategorias de produtos;
- HF58 — multicategorias da Galeria;
- HF57 — categorias sem limite;
- HF56 — lightbox da Galeria;
- HF55 — exclusão individual de fotos da Galeria interna;
- Template Mestre Comercial HF7 congelado e Template Anna homologado.
