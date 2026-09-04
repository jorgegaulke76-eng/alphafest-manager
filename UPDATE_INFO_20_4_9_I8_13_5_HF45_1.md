# 20.4.9-I8.13.5-HF45.1 — Folha A4 de revisão do Catálogo

## Objetivo
Facilitar a conferência manual de categorias e subcategorias antes da reorganização da vitrine do site.

## O que foi adicionado
- Na aba `Catálogo → Produtos`, botão `🖨️ Baixar folha de revisão A4 — todos os produtos`.
- PDF A4 simples com **todos os produtos cadastrados**, ativos e inativos.
- **6 produtos por página**.
- Para cada produto: foto pequena, nome, categoria atual, subcategoria atual, status e espaço para a Anna anotar a categoria e subcategoria corretas.
- Sem preço, descrição comercial, material ou outros dados desnecessários para esta revisão.

## Segurança / regressão
- A geração é somente leitura e não altera o Catálogo Oficial.
- HF44 permanece intacto: publicação assistida Cloudflare, Worker `alphafest-novo`, ZIP de fallback e regras do domínio não foram modificados.
- Nenhuma mudança ainda foi feita na navegação do site; esta etapa serve apenas para preparar a classificação correta.
