# 20.4.9-I8.13.2-HF2 — Ficha Técnica Opcional + Consumo por Pedido

## Objetivo
A Ficha Técnica deixa de ser uma obrigação universal e passa a funcionar como **receita padrão opcional**. A decisão de consumo é feita por pedido, porque o mesmo produto pode ter comportamentos diferentes conforme a execução real — por exemplo, cliente fornece o material, serviço é somente impressão ou existem insumos específicos naquele pedido.

## Três caminhos de liberação
1. **Usar Ficha Técnica padrão** — quando todos os itens possuem ficha ativa com materiais controlados.
2. **Informar materiais deste pedido** — escolhe materiais e quantidades apenas para a proposta atual; não altera Catálogo nem Ficha Técnica.
3. **Sem consumo de estoque controlado neste pedido** — libera o pedido sem criar reserva nem baixa física.

## Segurança
- O vínculo seguro com o Catálogo Oficial continua obrigatório.
- A Ficha Técnica, sozinha, não bloqueia mais a produção.
- A decisão fica auditada no consumo do pedido (`modo_consumo`).
- Materiais manuais usam os materiais oficiais do Estoque e entram no mesmo fluxo Reserva → Consumo Real.
- O modo sem consumo cria uma liberação auditada com necessidades vazias e nunca inventa movimentação de estoque.
- Alterações futuras na Ficha Técnica só geram alerta de divergência em pedidos que realmente foram liberados pelo modo `ficha_padrao`.
- Registros legados sem `modo_consumo` continuam tratados como Ficha Técnica para compatibilidade.

## Fluxo físico preservado
Quando há materiais: **confirmar = reservar saldo livre** e **iniciar produção = baixar fisicamente**. Quando o pedido é confirmado como sem consumo controlado, iniciar produção segue sem qualquer baixa de estoque.

## Migração
Nenhuma migração de banco e nenhuma alteração automática nos JSONs operacionais da base.
