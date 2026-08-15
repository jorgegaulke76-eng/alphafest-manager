# 20.4.9-H — Identidade e Padronização Assistida de Produtos

Base: Atual 2049G1 aprovada.

## Por que esta etapa vem antes de novas automações do THU
Variações de nome do mesmo produto podem dividir ranking, faturamento, histórico e busca.
A correção foi feita sem reescrever propostas antigas.

## Novo conceito: produto oficial + aliases
Cada produto do Catálogo pode ter `Aliases` (nomes alternativos confirmados).

Exemplo:
- Produto oficial: PAPEL DE ARROZ
- Alias: PAPEL ARROZ

O histórico continua exatamente como foi criado, mas Relatórios e THU podem reconhecer ambos como o mesmo produto.

## Relatórios
- rankings de Produtos mais orçados e Produtos efetivamente pagos passam a consolidar aliases confirmados;
- mostra quantos itens foram consolidados no período;
- a auditoria virou `Padronizar nomes de produtos com segurança`;
- para cada grupo suspeito, o usuário escolhe um produto oficial do Catálogo;
- `Confirmar equivalência` grava somente o alias no Catálogo;
- propostas antigas não são renomeadas nem alteradas;
- equivalências já confirmadas ficam visíveis.

## Catálogo
- Jorge e Anna podem visualizar/editar nomes alternativos;
- buscas do Catálogo e Pesquisa Global reconhecem aliases;
- cards do Catálogo consolidam estatística histórica usando nome oficial + aliases;
- o rótulo enganoso `Vendido` foi trocado por `Orçado histórico`, pois a estatística usa propostas;
- se um produto for renomeado, o nome anterior é preservado automaticamente como alias;
- aliases conflitantes com outro produto oficial são rejeitados para evitar mistura de dados.

## THU
- busca por produto reconhece nome oficial e aliases;
- correlação com Biblioteca também considera aliases confirmados.

## Segurança
- nenhum histórico é reescrito;
- nenhum produto é mesclado automaticamente;
- se duas variações já forem nomes oficiais de produtos diferentes, o sistema bloqueia a vinculação e exige revisão manual.
