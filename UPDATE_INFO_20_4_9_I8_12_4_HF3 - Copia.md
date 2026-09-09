# AlphaFest Manager 20.4.9-I8.12.4-HF3 — Compras integradas à Ficha Técnica e saneamento de materiais

## Motivo do hotfix
O HF2 homologou a fila de liberação e a resolução Saneamento → Produto Oficial → Ficha Técnica. Durante o teste real de compra, porém, a entrada de estoque ainda usava o texto digitado no campo “Produto / material comprado”. Isso permitia criar um material paralelo mesmo quando o produto de venda relacionado já possuía um material oficial na Ficha Técnica.

Exemplo observado no teste:
- pendência do pedido: `CANECA CERAMICA`;
- compra digitada como `CANECA PORCELANA` / `CANECA PORCELANA COM ALÇA`;
- resultado antigo: a compra criava/abastecia outro material e a pendência de `CANECA CERAMICA` não era quitada.

## Regra oficial da entrada por compra
Quando “Lançar esta compra como entrada de estoque” estiver marcado:
1. o produto de venda relacionado é resolvido no Catálogo Oficial;
2. a Ficha Técnica desse produto é consultada;
3. os materiais técnicos existentes aparecem primeiro como destino da entrada;
4. se houver exatamente um material técnico, ele é sugerido automaticamente;
5. se houver mais de um material, o usuário precisa escolher qual foi realmente comprado;
6. se não houver material técnico, o usuário escolhe explicitamente um material existente ou a opção de criar um material novo;
7. o nome digitado na compra não cria mais uma duplicata silenciosamente.

A unidade da compra precisa ser igual à unidade do material controlado. Não existe conversão implícita.

## Pendências automáticas
A entrada é registrada diretamente no material escolhido. O mecanismo já homologado da I8.12.4 continua sendo executado após a entrada:
- saldo físico nunca fica negativo;
- pedidos pendentes são atendidos por ordem de confirmação;
- a entrada é usada automaticamente para reduzir a pendência do material correto.

Exemplo esperado:
- `CANECA CERAMICA`: saldo 0 / pendente 5;
- compra de 3 unidades vinculada a `CANECA PORCELANA PERSONALIZADA`;
- Ficha Técnica aponta para `CANECA CERAMICA`;
- entrada +3 em `CANECA CERAMICA`;
- baixa automática 3 para o pedido;
- saldo físico 0 / pendente 2.

## Consolidação de duplicatas existentes
Foi adicionado o bloco `🧹 Consolidar material duplicado` para corrigir materiais já criados com nomes diferentes.
- O histórico antigo não é apagado.
- O saldo da duplicata é transferido por duas novas movimentações de reclassificação.
- O material de origem fica inativo e aponta para o material oficial de destino.
- Materiais usados por Ficha Técnica ou com pendência própria não podem ser desativados silenciosamente.
- Após a consolidação, o saldo transferido pode atender automaticamente pendências do destino.
- O último custo do material oficial também reconhece compras históricas dos nomes consolidados, sem alterar o texto original da compra.

## Rastreabilidade
Novas compras com entrada de estoque gravam:
- material de estoque de destino;
- origem do vínculo (`ficha_tecnica`, `material_existente` ou `novo_material_explicito`);
- item original digitado continua preservado;
- auditoria registra item comprado, material de destino e quantidade.

## Regras preservadas
- Catálogo Oficial continua sendo a única fonte de produto/preço de venda.
- Ficha Técnica continua sendo a regra de consumo.
- Compra/custo nunca altera preço oficial automaticamente.
- Fila de liberação continua: Aprovado = SIM + Entregue = NÃO + consumo não confirmado.
- Confirmação/estorno de consumo permanecem rastreáveis.
