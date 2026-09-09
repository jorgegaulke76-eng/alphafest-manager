# 20.4.9-I8.13.2-CAT1-HF4

## Produto assistido no Novo Orçamento

- Campo de produto agora é híbrido no Jorge e na Anna.
- `Produto do Catálogo Oficial` é pesquisável: o usuário pode começar a digitar para filtrar nomes oficiais e aliases.
- Aliases aparecem como atalhos, mas a proposta salva o nome oficial, reduzindo variações de digitação para o mesmo produto.
- `Produto livre / novo` continua disponível quando o item ainda não existe no Catálogo Oficial.
- Texto livre que corresponda exatamente a um nome/alias conhecido é normalizado automaticamente para o produto oficial.
- Itens passam a registrar metadados auxiliares (`produto_origem`, `produto_digitado`, `produto_catalogo_id`) sem alterar a compatibilidade do campo `produto` existente.
- A escolha do Catálogo tem prioridade quando os dois campos são preenchidos.
- Nenhum produto é criado automaticamente no Catálogo; produto livre continua seguindo o fluxo de saneamento/cadastro posterior.

## Regra de segurança

A nova assistência reduz erros e duplicidades, mas não bloqueia a operação: se o produto não existir no Catálogo, o orçamento pode ser criado normalmente por texto livre.
