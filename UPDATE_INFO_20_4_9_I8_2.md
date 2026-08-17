# 20.4.9-I8.2 — Fotos Históricas + Ordem Alfabética

Base: 20.4.9-I8.1.

## 1. Foto do catálogo histórico
Ao preparar um produto novo a partir do Acervo Histórico, a aba
`Arquivos, artes e fotos` agora mostra a imagem original da página.

### Página de produto único
A opção:
`Aproveitar esta imagem no banco de fotos do produto`
vem marcada por padrão.

Ao clicar em `Salvar no Catálogo Oficial`, a imagem:
- é copiada pelo mesmo pipeline persistente das fotos oficiais;
- entra na galeria `Imagens` do produto;
- fica disponível na listagem e nos catálogos para cliente;
- continua rastreada pela fonte histórica.

### Página com vários produtos
A opção existe, porém fica desmarcada por padrão.
O THU não presume que a página inteira seja foto adequada de um item específico.

## 2. Produtos já cadastrados pela I8.1
Na revisão de um produto existente, o Acervo oferece:
`Adicionar a imagem histórica ao banco de fotos do produto`.

Se o produto estiver sem foto e a página for de produto único, a opção vem marcada
por padrão. Portanto produtos já criados na I8.1, como Long Drink, podem receber a
foto sem recriar o cadastro.

## 3. Persistência
A prévia histórica não é apenas apontada como caminho local.
Ao confirmar, ela passa pelo pipeline de armazenamento persistente do Catálogo.

## 4. Ordem alfabética
Foi aplicada ordem alfabética preservando os índices internos do banco em:
- Catálogo > Produtos;
- Central da Anna > Visualizar produtos;
- seleção de produtos para catálogo de cliente;
- catálogo HTML gerado;
- catálogo HTML completo.

Editar, Lixeira e Orçamento continuam usando o índice real do produto, portanto
a ordenação visual não altera os vínculos internos.

## Segurança mantida
- preço histórico não vira preço atual;
- mínimo histórico não vira regra;
- foto de página multiproduto não é selecionada automaticamente;
- nenhuma foto histórica entra sem confirmação no formulário/revisão.
