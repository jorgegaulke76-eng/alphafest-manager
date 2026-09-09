# AlphaFest Manager 20.4.9-I8.12.5

## Central de Necessidades de Compras

- Nova Central derivada das pendências reais dos consumos de pedidos confirmados pela I8.12.4.
- Não cria novo banco nem segunda fonte de pedidos/estoque: a necessidade some automaticamente quando entradas de estoque quitam a pendência.
- Agrupa por material: quantidade pendente, pedidos envolvidos, próxima entrega e prioridade por prazo.
- Exibe último fornecedor e último custo conhecidos a partir do histórico oficial de Compras.
- Calcula valor estimado de compra somente quando existe custo conhecido; itens sem custo ficam explicitamente sem estimativa.
- Detalha quais pedidos/clientes compõem cada necessidade e a falta correspondente de cada pedido.
- Ação “Preparar compra deste material” preenche material, quantidade pendente, fornecedor/custo conhecidos, produtos relacionados e destino correto do estoque; Jorge ainda revisa e confirma a compra.
- Central do Jorge recebe resumo agregado dos materiais faltantes usando a mesma fonte única.
- Nenhum preço do Catálogo Oficial é alterado automaticamente.
- Nenhum novo JSON de dados foi criado.
