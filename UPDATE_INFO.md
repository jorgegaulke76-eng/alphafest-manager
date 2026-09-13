# AlphaFest Manager — HF59

## Central do Site simplificada + produtos em múltiplas categorias

Atualização incremental sobre a HF58. Mantém as regras de negócio e módulos homologados e concentra a Central do Site apenas no que é usado no dia a dia.

### Central do Site
- mantém o painel de **Métricas privadas**;
- remove da tela as prévias antigas HF40/HF45/HF47/HF48, staging histórico, listas auxiliares e comparação antiga do site;
- cria um fluxo único **Preparar / atualizar prévia → Conferir Desktop/Celular → Publicar site agora**;
- mantém acesso ao site atual, conexão Cloudflare e ZIP manual de contingência;
- preserva o motor de publicação HF44 e todas as proteções existentes.

### Produtos em múltiplas categorias do site
- o produto continua com uma **Categoria principal** no Catálogo;
- novo campo **Exibir também nestas categorias do site** permite associar o mesmo produto a outras categorias sem duplicar cadastro;
- no site, o produto aparece em todas as categorias marcadas e apenas uma vez em **Todos os produtos**;
- contadores e cards de categorias passam a considerar as categorias extras;
- a mesma subcategoria do produto continua válida nas categorias em que ele for exibido;
- compatibilidade: cadastros que já tenham categorias separadas por vírgula, ponto e vírgula, `|` ou quebra de linha são interpretados sem perder informação e, ao salvar, ficam normalizados no novo campo.

### Preservado
- HF58 — Galeria em múltiplas categorias;
- HF57 — categorias do site sem limite de 12;
- HF56 — lightbox da Galeria pública;
- HF55 — exclusão individual de foto na Galeria interna;
- HF54 e demais otimizações homologadas;
- Template Mestre Comercial HF7 congelado;
- Template Anna homologado;
- Catálogo como Fonte Única, métricas, WhatsApp, carrossel, Produto → Galeria e publicação Cloudflare HF44.
