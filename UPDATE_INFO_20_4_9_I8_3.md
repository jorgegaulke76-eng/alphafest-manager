# 20.4.9-I8.3 — Recuperação Retroativa de Fotos Históricas

Base: Atual 2049I82 enviada e testada pelo usuário.

## Causa
A I8.2 incorporava a foto histórica corretamente em novos cadastros criados
depois da atualização, mas produtos já cadastrados pela I8.1 sem foto permaneciam
com `0 foto(s)`.

## Correção
Foi criada recuperação retroativa segura.

Só recebe foto automaticamente o produto que:
- está sem nenhuma imagem;
- possui `FontesHistoricasCatalogos`;
- possui preview histórico existente;
- fonte é de página de produto único.

Páginas multiproduto continuam ignoradas automaticamente.

## Onde executa
A verificação ocorre uma vez por sessão ao abrir:
- Catálogo principal;
- Visualizar Catálogo da Anna.

Também existe no Acervo:
`📸 Recuperar fotos históricas seguras`

## Rastreabilidade
A imagem recuperada registra:
- catálogo histórico;
- página;
- preview de origem;
- usuário;
- data/hora;
- ação;
- regra de segurança.

Também fica registrada em:
- `BancoImagensHistorico`;
- `HistoricoEnriquecimentoCatalogos`.

## O que NÃO muda
- preço oficial;
- quantidade mínima;
- descrição;
- material;
- campanhas;
- aliases;
- vínculos existentes.

A correção atua exclusivamente em produtos sem foto.
