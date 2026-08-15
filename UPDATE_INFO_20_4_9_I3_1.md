# 20.4.9-I3.1 — Limpeza e Inteligência do Acervo

Base: Atual 2049I3.

## 1. Hotfix do erro removeChild
A análise do site não tenta mais reconstruir o resultado no mesmo ciclo do botão/spinner.
Depois de concluir a leitura, o sistema salva o scan e executa um novo ciclo limpo do Streamlit.

Objetivo: evitar o conflito de reconciliação do frontend que gerava:
`NotFoundError: Failed to execute 'removeChild' on 'Node'`.

## 2. Logos e imagens globais
- logos e ícones sociais óbvios são removidos;
- imagens idênticas/repetidas em muitas páginas são detectadas por identidade da URL Wix;
- um ativo só é tratado como global quando aparece em pelo menos 5 páginas e >=35% das páginas válidas;
- o painel mostra quantos ativos globais foram filtrados.

## 3. Títulos corretos
Headings genéricos como `Páginas`, `Produtos`, `Galeria` e `Fotos` não são mais usados como nome principal.
O THU prioriza o texto específico do menu, depois heading útil, título e por último o slug da URL.

## 4. Classificação do acervo
As páginas passam a ser separadas em:
- Produto;
- Categoria;
- Serviço;
- Campanha;
- Estrutura.

Categorias e serviços não contam como produtos ausentes e não recebem botão de cadastro automático.

## 5. Cadastro seguro
`Cadastrar produto` aparece somente quando:
- a página foi classificada como Produto;
- a confiança da classificação é >=85%;
- não existe correspondência segura no Catálogo.

## 6. Site × Catálogo
O matching usa:
- nome da página;
- texto do menu;
- título HTML;
- headings úteis;
- nome oficial + aliases do Catálogo;
- normalização de plural e termos genéricos.

## 7. Compatibilidade com scans antigos
Scans feitos na I3 são reprocessados pelas regras I3.1 ao serem exibidos.
Não é obrigatório perder o scan anterior para aproveitar a limpeza.

## 8. Interface
O módulo passa a usar `Assistente THU` nos títulos para eliminar a leitura visual ambígua observada no navegador.

## Segurança
- nenhuma página vira produto automaticamente;
- nenhuma categoria ou serviço vira produto automaticamente;
- nenhuma foto é importada sem seleção e confirmação;
- o Catálogo continua sendo a fonte oficial.
