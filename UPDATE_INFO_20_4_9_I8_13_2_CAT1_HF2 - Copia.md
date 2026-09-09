# 20.4.9-I8.13.2-CAT1-HF2

Correção de isolamento de cadastros vindos do Acervo Histórico.

- Cada produto/Kit Festa preparado recebe um token de rascunho exclusivo.
- Widgets de um cadastro novo não reutilizam mais valores do kit anterior.
- Após salvar, o estado temporário daquele rascunho é limpo.
- Novo produto recebe `CatalogoId` persistente próprio.
- Cadastro novo com nome/alias já existente é bloqueado em vez de alterar silenciosamente outro produto.
- Nenhum JSON operacional da base é migrado ou regravado pelo pacote.
