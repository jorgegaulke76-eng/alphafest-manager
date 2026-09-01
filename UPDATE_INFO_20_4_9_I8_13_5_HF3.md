# 20.4.9-I8.13.5-HF3 — Status + Persistência de Propostas Modular

## Objetivo
Continuar a modularização iniciada na I8.13.5 sem alterar o comportamento operacional homologado.

## Alterações
- Novo `proposal_status_service.py`: concentra normalização, snapshots, transições, carimbos e verificação dos quatro status oficiais.
- Novo `proposal_persistence_service.py`: concentra a atualização segura de uma única proposta, preferindo compare-and-swap do banco e usando fallback somente sobre leitura fresca.
- `app.py` passa a atuar como orquestrador: materiais, UI, auditoria e navegação permanecem nele, enquanto regras de status/persistência são delegadas aos serviços puros.
- A confirmação pós-gravação continua obrigatória: se o banco não refletir exatamente os status solicitados, o Manager não confirma a baixa.
- Nenhuma mudança de banco, SQL, status oficial, estoque ou tela.

## Regras preservadas
- Aprovado → Pago → Pronto → Entregue.
- Entregue implica Pronto.
- Pronto/Entregue novos continuam respeitando consumo/reserva de materiais.
- Mensalistas continuam com pagamento controlado pelo fechamento mensal.
- Histórico/Proposta continua sendo a fonte oficial.

## Validação
- Testes de regressão dos serviços operacionais e de persistência.
- Compilação/AST de todos os arquivos Python.
- JSONs operacionais preservados sem alteração.
