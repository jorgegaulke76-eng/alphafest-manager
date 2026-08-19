# AlphaFest Manager 20.4.9-I8.12.4 — Baixa de Estoque por Pedido

## Objetivo
Ligar pedidos aprovados às Fichas Técnicas homologadas sem permitir saldo de estoque negativo e sem criar baixas escondidas apenas pela aprovação da proposta.

## Fluxo homologável
1. Pedido aprovado continua sem movimentar estoque automaticamente.
2. Jorge abre **Gestão → Compras, Custos & Estoque** e revisa a prévia do consumo.
3. Ao confirmar, o Manager calcula a necessidade por Ficha Técnica.
4. O saldo disponível é baixado até o limite existente.
5. O restante fica registrado como **pendência do pedido**, sem saldo negativo.
6. Qualquer nova entrada/ajuste positivo de estoque tenta quitar automaticamente as pendências mais antigas (FIFO).
7. Ao quitar parcialmente ou totalmente, Pedido, Estoque, Histórico, Fluxo e Central passam a refletir o mesmo estado.

## Estados do consumo
- ⚪ Consumo não confirmado
- 🟠 Material pendente
- 🟡 Parcialmente atendido
- 🟢 Materiais atendidos
- ⚪ Estornado

## Segurança e rastreabilidade
- Confirmação de consumo é manual e somente depois da aprovação do pedido.
- Pedido com consumo confirmado não pode ser excluído sem antes estornar o consumo.
- Estorno devolve as baixas já realizadas ao estoque, cancela a pendência remanescente e preserva o histórico.
- Se o pedido ou a Ficha Técnica mudar após a confirmação, o Manager alerta para estornar e confirmar novamente.
- Baixas de pedido não podem ser estornadas pelo estorno genérico de movimentação; usam o fluxo próprio do pedido.
- O Catálogo Oficial e preços de venda não são alterados.

## Comunicação entre telas
- Estoque mostra saldo disponível e quantidade pendente em pedidos por material.
- Central do Jorge alerta pedidos aguardando material e consumos que precisam revisão.
- Histórico e Fluxo exibem o estado dos materiais do pedido.
- A Central/linhas da Anna exibem somente o status operacional dos materiais, sem controles administrativos de confirmação/estorno.
- Entradas que regularizam pendências geram mensagem operacional e eventos de auditoria/timeline.

## Banco novo
- `consumo_pedidos_db.json` — guarda somente a necessidade confirmada do pedido, referências de materiais, assinatura da confirmação e eventos. As baixas físicas continuam registradas em `estoque_db.json`.
