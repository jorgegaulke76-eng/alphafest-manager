# 20.4.9-I8.13.5-HF5 — Produção + Etapas + Conclusão modular

Base: 20.4.9-I8.13.5-HF4 homologada.

## Objetivo

Reduzir o acoplamento do `app.py` na área crítica de produção sem alterar as regras de negócio homologadas.

## Novo serviço

`producao_operacional_service.py`

Concentra regras puras e testáveis para:

- validar mudanças manuais do Fluxo contra Aprovado/Entregue oficiais;
- decidir quais etapas representam produção real e exigem validação/consumo de materiais;
- decidir quando o conjunto de itens autoriza `Pronto = SIM` ou `Entregue = SIM`;
- retirar `Pronto` oficial quando uma produção é reaberta, sem reabrir `Entregue`;
- planejar os atalhos da Central de Produção (`Iniciar produção` e `Marcar pedido pronto`) sem persistir dados.

## Regras preservadas

1. Histórico/Proposta continua sendo a fonte oficial de Aprovado, Pago, Pronto e Entregue.
2. `producao_db` continua guardando apenas a etapa manual do trabalho.
3. Entrar em produção converte reserva em consumo físico pelo motor de materiais já homologado.
4. `Pronto` oficial só é marcado quando todos os itens do pedido estão Pronto/Entregue.
5. `Entregue` oficial só é marcado quando todos os itens estão Entregue.
6. Reabrir a produção no Fluxo remove `Pronto` oficial somente se o pedido ainda não estiver Entregue.
7. A Central de Produção e o Fluxo usam agora o mesmo serviço de regras de etapa.

## Dados

Nenhum JSON operacional é migrado ou regravado pela atualização. Nenhum SQL novo é necessário.
