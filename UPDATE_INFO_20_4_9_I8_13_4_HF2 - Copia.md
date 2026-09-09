# 20.4.9-I8.13.4-HF2 — Integração Fluxo ↔ Histórico

## Objetivo
Fazer Fluxo de Pedidos e Histórico de Pedidos trabalharem como duas visões da mesma operação, sem criar uma segunda fonte de status.

## Correções
- Proposta não aprovada permanece como `Pedido recebido` no Fluxo; não entra artificialmente em arte/produção.
- Aprovado oficial libera/restaura a etapa produtiva; remover aprovação recolhe o pedido e preserva a etapa anterior.
- `Aguardando aprovação` no Fluxo passa a ficar claramente reservado à aprovação da arte.
- Indicadores de atraso/produção contam apenas pedidos oficialmente aprovados.
- Fluxo mostra os quatro status oficiais do Histórico em cada item.
- Histórico mostra a etapa atual do Fluxo por item.
- Navegação direta Fluxo → Histórico e Histórico → Fluxo com o mesmo pedido selecionado.
- Mudanças de etapa e prioridade do Fluxo entram na auditoria oficial da proposta.
- Gravação de uma tarefa do Fluxo usa atualização com leitura fresca/CAS quando disponível, reduzindo conflito entre sessões.
- Inclui a correção da HF1: Histórico exibe a Linha do Tempo Oficial com usuário e antes → depois.

## Regras preservadas
- Aprovado → Pago → Pronto → Entregue continuam como status oficiais da proposta.
- Etapas de arte/produção continuam no `producao_db` e não viram novos status comerciais.
- Pronto/Entregue continuam sincronizando do Fluxo para o Histórico quando todos os itens atingem o marco.
- Sem SQL novo, sem API paga e sem custo recorrente.
