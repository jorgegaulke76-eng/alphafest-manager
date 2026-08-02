# Atualização FestManager 7.0.0 — Relacionamentos e Política de Atendimento

- Base anterior: 6.1.0
- Nova versão: 7.0.0
- Versão dos dados: 4
- Migração: aditiva e automática
- Dados existentes: preservados

## Arquivos do pacote
- app.py
- cloud_db.py
- requirements.txt
- VERSAO.txt
- CHANGELOG.md
- ROADMAP.md
- UPDATE_INFO.md

## Novidades
- Clientes passa a se chamar Relacionamentos.
- Um cadastro pode ter vários papéis: cliente, fornecedor, parceiro, prestador, transportadora, influenciador, concorrente monitorado e outros.
- Política individual de atendimento: normal, somente manual, atenção, monitorado ou bloqueado.
- Permissões independentes para resposta, catálogo, orçamento e campanhas.
- Regras de pagamento antecipado e aprovação do gestor.
- Dados de fornecedor no mesmo cadastro, inclusive quando também for cliente.
- Alpha e Central Multicanal consultam a política antes de responder ou criar orçamento.
