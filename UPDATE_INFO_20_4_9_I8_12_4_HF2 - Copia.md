# AlphaFest Manager 20.4.9-I8.12.4-HF2 — Fila oficial de liberação de consumo

## Motivo do hotfix
A fila de consumo ainda misturava regras operacionais antigas: podia manter pedidos já confirmados no seletor e podia excluir propostas aprovadas por filtros adicionais de encerramento. Isso causou divergência entre a proposta aprovada na Anna e a fila de liberação do Jorge.

## Regra oficial da fila
Uma proposta entra na fila somente quando:
- `Aprovado = SIM`;
- `Entregue = NÃO`;
- ainda não existe consumo ativo confirmado para a proposta.

A proposta sai imediatamente da fila quando:
1. o consumo é confirmado; ou
2. o status `Entregue` é marcado.

Nenhuma data, idade da proposta, data de entrega ou outro status participa da decisão de entrada na fila.

## Saneamento e Ficha Técnica
A elegibilidade da fila não depende do nome do produto nem da existência da ficha. Depois que a proposta entra:
- Item da proposta → Saneamento → Produto Oficial → Ficha Técnica → necessidade de estoque.
- Se o Saneamento/Catálogo não conseguir resolver o item, a proposta continua visível com liberação bloqueada.
- Se o produto oficial não possuir Ficha Técnica, a proposta continua visível com liberação bloqueada.
- Não é mais possível ignorar silenciosamente item sem ficha para confirmar um consumo parcial.

## Comunicação entre telas
- Anna/Histórico/Fluxo mostram `aguardando liberação de consumo` quando a proposta aprovada está apta à fila.
- Proposta já entregue sem consumo confirmado aparece como `fora da fila de liberação (proposta entregue)`.
- Central do Jorge mostra quantas propostas aprovadas aguardam liberação e diferencia: pronta, vínculo pendente e ficha pendente.
- Pedidos com consumo confirmado permanecem rastreáveis no histórico próprio, mas não ocupam o seletor de liberação.

## Segurança preservada
- Aprovação não movimenta estoque sozinha.
- Confirmação de consumo continua exclusiva do fluxo administrativo.
- Estoque físico nunca fica negativo.
- Falta de material vira pendência; entradas posteriores continuam regularizando automaticamente.
- Estorno preserva histórico.
- Nenhum preço ou dado do Catálogo Oficial é alterado.
