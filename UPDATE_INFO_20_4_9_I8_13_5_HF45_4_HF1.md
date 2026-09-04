# AlphaFest Manager — 20.4.9-I8.13.5-HF45.4-HF1

## Correção da navegação Categoria → Subcategoria

- Corrige a prévia HF45.4 para ocultar de verdade as subcategorias que não pertencem à categoria selecionada.
- A causa era visual: o atributo `hidden` era aplicado corretamente pelo JavaScript, mas o CSS de `.subfilter` forçava `display:inline-flex` e fazia os botões ocultos continuarem visíveis.
- Agora, ao escolher uma categoria, a etapa 2 mostra somente `Todas` e as subcategorias daquela categoria.
- HF44 e a publicação oficial permanecem inalterados.
