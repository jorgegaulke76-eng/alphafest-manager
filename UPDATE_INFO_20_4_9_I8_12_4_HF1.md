# AlphaFest Manager 20.4.9-I8.12.4-HF1 — Saneamento integrado ao consumo por pedido

## Motivo do hotfix
Uma proposta aprovada podia não encontrar a Ficha Técnica quando o nome digitado no histórico não era idêntico ao nome oficial do Catálogo, mesmo existindo uma correlação clara pelo Saneamento. Isso fazia telas operacionais tratarem o item como ausente ou não conseguirem montar a necessidade de estoque.

## Correção arquitetural
- Cria uma resolução única de produto para as telas operacionais.
- Prioridade absoluta para **Nome Oficial** e **Aliases confirmados** no Catálogo.
- Quando não houver correspondência direta, aplica correlação conservadora de Saneamento por nome, alias, categoria, subcategoria, variações e palavras-chave.
- A correlação automática só é aceita quando a evidência é forte e o candidato é único; em caso de empate/ambiguidade, o sistema não vincula silenciosamente.
- Nenhum alias é gravado automaticamente e a proposta original não é modificada.

## Comunicação entre telas
- Anna deixa de receber aviso falso de “produto fora do Catálogo” quando o Saneamento consegue resolver o item com segurança.
- Quando a correlação automática for usada, a operação pode ver `item da proposta → produto oficial`.
- Consumo por pedido usa o produto oficial resolvido para localizar a Ficha Técnica.
- THU e rotinas que consultam existência de produto passam a usar a mesma resolução, evitando divergência entre telas.
- O módulo de padronização continua diferenciando **alias realmente gravado** de uma correlação automática do Saneamento.

## Cenário de homologação
Exemplo esperado:
- Item na proposta: `CANECA CERAMICA BRANCA COM ALÇA`
- Produto oficial: `CANECA PORCELANA PERSONALIZADA`
- Categoria oficial: `CANECAS PORCELANA COM ALÇA`
- Ficha Técnica: 1 un de `CANECA CERAMICA` por unidade vendida
- Pedido com quantidade 5 deve montar necessidade de **5 un** de `CANECA CERAMICA`.

## Segurança preservada
- Pedido aprovado não baixa estoque sozinho.
- Confirmação de consumo continua manual no Jorge.
- Estoque físico nunca fica negativo.
- Falta de material continua virando pendência e novas entradas continuam regularizando-a automaticamente.
- Preços e dados oficiais do Catálogo não são alterados por este hotfix.
