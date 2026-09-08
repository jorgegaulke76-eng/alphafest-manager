# 20.4.9-I8.13.5-HF52.1-HF3-HF1 — correção da busca pública

## Correção
- corrige falso positivo da busca inteligente que podia manter produtos não relacionados visíveis (ex.: buscar `CANECA` e ainda exibir itens genéricos);
- remove a regra permissiva baseada apenas nos 3 primeiros caracteres;
- impede que palavras muito curtas do índice (`a`, `e`, etc.) façam uma consulta maior coincidir indevidamente;
- a busca do cabeçalho agora sempre volta para **Todos** antes de aplicar o termo, tornando-a global mesmo se o cliente estava dentro de uma categoria/subcategoria;
- preserva tolerância a pequenos erros de digitação, métricas de busca HF52.1-HF3 e todo o visual homologado.

## Banco
Nenhuma alteração no Supabase é necessária. O SQL do HF52.1-HF3 já executado continua válido.
