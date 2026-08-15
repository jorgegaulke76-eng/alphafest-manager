# 20.4.9-H2 — Resolver Produto Ausente no Catálogo

Base: Atual 2049H1 aprovada.

## Novo fluxo
Quando a Padronização de Produtos não encontra um produto oficial compatível com segurança:

1. aparece `➕ Criar produto oficial`;
2. o sistema escolhe apenas uma das variações já existentes no histórico como sugestão de nome;
3. o Cadastro oficial é aberto com esse nome pré-preenchido;
4. o usuário continua responsável por revisar nome, categoria, material, valor, campanhas e demais dados;
5. ao salvar, o sistema retorna para Relatórios;
6. a área de Padronização volta aberta;
7. o novo produto passa a aparecer como opção/sugestão;
8. a equivalência só é gravada quando o usuário clicar em `Confirmar equivalência`.

## Segurança
- nenhum produto é criado automaticamente;
- nenhum alias é confirmado automaticamente;
- nenhuma proposta histórica é alterada;
- cancelar o novo cadastro limpa o retorno pendente;
- o nome sugerido vem do próprio histórico e continua editável.
