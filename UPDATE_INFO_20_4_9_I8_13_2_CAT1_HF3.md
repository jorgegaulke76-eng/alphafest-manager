# 20.4.9-I8.13.2-CAT1-HF3

Hotfix — separação definitiva entre Produto Comercial e Material de Estoque.

- Produto vendido ao cliente continua exigindo correspondência segura no Catálogo Oficial.
- Item que não existe no Catálogo, mas corresponde de forma única a um material ativo do Estoque, é reconhecido como material/insumo operacional.
- Material de estoque não precisa ser cadastrado como produto comercial apenas para liberar reserva ou produção.
- Item de material presente na proposta não cria consumo adicional automaticamente; a quantidade continua vindo da Ficha Técnica ou da decisão manual do pedido, evitando dupla reserva/baixa.
- Se houver dois materiais ativos com o mesmo nome, o sistema não escolhe no chute e mantém a trava para revisão.
- THU e Central de materiais deixam de sugerir cadastro no Catálogo para material operacional reconhecido.
- Nenhum JSON operacional é migrado ou regravado pelo pacote.
