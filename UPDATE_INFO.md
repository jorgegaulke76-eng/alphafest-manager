# AlphaFest Manager — HF53.3-HF8-HF58

## Galeria — um trabalho em múltiplas categorias

Evolução isolada da Galeria, baseada na HF57, sem duplicar trabalhos e sem alterar a categoria principal do produto.

### Entrega
- cada trabalho mantém sua **categoria principal** atual;
- adiciona o campo **Exibir também em outras categorias do site**;
- permite selecionar uma ou várias categorias adicionais tanto ao registrar um novo trabalho quanto em trabalhos já existentes;
- no site, o mesmo trabalho aparece ao filtrar qualquer categoria marcada;
- em **Todas as categorias**, o trabalho continua aparecendo apenas uma vez;
- o filtro interno da Galeria também encontra o trabalho pela categoria principal ou por qualquer categoria adicional;
- as categorias adicionais entram na busca/filtro público da Galeria sem duplicar fotos ou registros;
- nenhuma migração de banco é necessária: o novo campo é opcional e compatível com registros antigos.

### Preservado
- HF57 — categorias públicas sem limite fixo;
- HF56 — lightbox da Galeria pública;
- HF55 — exclusão individual de foto na Galeria interna;
- vínculo Produto → Galeria, filtros, busca, WhatsApp, métricas e publicação Cloudflare HF44;
- Template Mestre Comercial HF7 congelado;
- Template Anna homologado;
- nenhuma alteração nas regras de produção, estoque, financeiro, CRM ou pedidos.
