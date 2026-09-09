# 20.4.9-I8.13.5-HF45.3 — Prévia Categoria → Subcategoria

## Objetivo
Adiantar a nova organização do site enquanto a Anna revisa a folha A4, sem alterar o site oficial antes da classificação estar pronta.

## O que foi preparado
- Nova prévia na Central do Site: `🧭 Prévia Categoria → Subcategoria — HF45.3`.
- A prévia usa diretamente os campos `Categoria` e `Subcategoria` do Catálogo Oficial.
- Ao escolher uma categoria, aparece uma segunda linha apenas com as subcategorias daquela categoria.
- A busca continua funcionando por produto, categoria, subcategoria e descrição.
- Produtos sem subcategoria aparecem como `Sem subcategoria`, deixando pendências visíveis durante a revisão.
- Métricas mostram produtos da vitrine, categorias, subcategorias e quantos ainda não têm subcategoria.

## Segurança / produção
- Nenhuma alteração é publicada automaticamente.
- O HF44 continua gerando e publicando a navegação comercial anterior.
- A nova taxonomia só poderá virar produção em uma etapa posterior, depois da revisão da Anna e da aprovação visual do usuário.
- DNS, Cloudflare, Worker, WhatsApp, preços e demais dados permanecem intactos.
