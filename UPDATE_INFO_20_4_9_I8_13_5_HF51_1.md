# HF51.2 — Vitrine limpa + ficha comercial do produto

Objetivo: deixar a listagem pública mais visual e rápida, com apenas **foto + nome**, e concentrar informações comerciais na ficha aberta ao clicar no produto.

## Comportamento público
- Sem estrela/selo de Destaque nos cards da vitrine.
- Sem descrição, preço ou botão de orçamento na listagem.
- Clique/toque no produto abre ficha com foto ampliada, nome, Categoria/Subcategoria, descrição completa e WhatsApp.
- O preço aparece somente quando `ExibirPrecoSite` estiver ativo no Catálogo Oficial.
- Quando houver trabalho selecionado na Galeria, a ficha mostra “Ver trabalhos realizados”.
- A ficha sugere até 4 produtos relacionados, priorizando mesma subcategoria e depois mesma categoria.

## Segurança operacional
Nenhum cadastro paralelo foi criado. Categoria, Subcategoria, preço, descrição, foto, PublicarSite e ExibirPrecoSite continuam vindo do Catálogo Oficial. O motor HF44 e a publicação assistida permanecem preservados.
