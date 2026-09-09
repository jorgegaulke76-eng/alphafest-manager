# HF51.2 — Busca inteligente da vitrine

## Objetivo
Ajudar o cliente a encontrar produtos mesmo quando não conhece o nome oficial do Catálogo ou digita com pequena diferença.

## O que mudou
- A busca pública passa a considerar nome, descrição, Categoria, Subcategoria, Material e Processos.
- Também considera Aliases, Variações, Campanhas, Tema, Ocasião e Tags/Palavras-chave quando esses dados existem no Catálogo Oficial.
- Pequenos erros de digitação são tolerados no navegador, sem serviço externo e sem custo adicional.
- A busca do cabeçalho continua sincronizada com a busca da vitrine.
- Nenhum cadastro é alterado: a Fonte Única continua sendo o Catálogo Oficial.

## Segurança operacional
- Não publica automaticamente.
- HF44/Cloudflare, Catálogo, Galeria, Produto → Galeria, carrossel e edição rápida permanecem preservados.
