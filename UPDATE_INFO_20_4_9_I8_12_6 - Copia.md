# AlphaFest Manager 20.4.9-I8.12.6 — Planejamento de Compras por Necessidade

## Objetivo
Transformar a falta real já consolidada pela I8.12.5 em um fluxo controlado de solicitação ao fornecedor, sem confundir necessidade, pedido ao fornecedor e compra/entrada efetivamente recebida.

## Regras oficiais
- A falta real continua vindo exclusivamente dos consumos de pedidos confirmados (I8.12.4/I8.12.5).
- Registrar uma solicitação ao fornecedor **não movimenta estoque** e **não reduz pendência de pedido**.
- A Central mostra separadamente: **Falta real**, **Já solicitado** e **Ainda a solicitar**.
- Somente a compra/entrada realmente recebida movimenta estoque e pode regularizar pendências automaticamente.
- Recebimentos podem ser parciais; o saldo ainda não recebido continua em aberto no planejamento.
- Se a falta real zerar antes do recebimento, a solicitação ao fornecedor não é cancelada silenciosamente: o sistema alerta Jorge para revisar/cancelar.
- Compra vinculada a planejamento deve entrar no mesmo material oficial solicitado.
- Excluir uma compra vinculada reabre a quantidade correspondente no planejamento; restaurá-la volta a registrar o recebimento.
- Nenhuma regra altera automaticamente preço de venda no Catálogo Oficial.

## Comunicação entre telas
- Gestão → Compras, Custos & Estoque: Central completa, solicitações em aberto, recebimentos e histórico.
- Central do Jorge: resumo de falta real, quantidade já solicitada e ainda a solicitar.
- Proposta/Histórico/Fluxo (componente de materiais): informa quando materiais pendentes já possuem compra em andamento.

## Dados
Novo documento: `planejamento_compras_db.json`.
Ele armazena somente o estado operacional de solicitação/recebimento ao fornecedor e referencia `material_id`; não replica a fonte de pendência, estoque ou Catálogo Oficial.
