# 20.4.9-I8.13.4-HF5 — Auditoria oficial consolidada por pedido

## Objetivo
Fechar a I8.13.4 consolidando em uma única linha do tempo os eventos que já acontecem em módulos diferentes do Manager, sem criar status paralelo e sem alterar os dados operacionais existentes.

## O que mudou
- A Linha do Tempo Oficial da proposta passa a agregar eventos relacionados ao mesmo número de pedido vindos de Proposta, Estoque, Reserva de Materiais, Produção/Fluxo e Entregas.
- Eventos estruturados continuam exibindo `valor anterior → valor novo`, usuário, horário e origem.
- A confirmação de materiais passa a auditar `materiais.tratamento` e `materiais.situacao`.
- Estorno de reserva/consumo passa a auditar situação anterior → liberação estornada e controle ativo → estornado.
- O consumo físico no início da produção passa a registrar a mudança da situação dos materiais e `producao.consumo_estoque: Reservado → Consumido fisicamente`.
- Atalhos da Central de Produção passam a registrar cada mudança de etapa de item na auditoria oficial somente depois da gravação confirmada de `producao_db`.
- Eventos antigos continuam preservados abaixo da auditoria central.
- A tela global de Auditoria passa a pesquisar também dentro dos detalhes/contextos e exibe a origem da alteração.
- Reconciliações de reserva que relacionam vários pedidos podem ser encontradas na linha do tempo de cada pedido relacionado.

## Segurança
- Nenhuma migração de dados.
- Nenhum SQL novo.
- Nenhuma alteração nos JSONs operacionais do pacote.
- Mantém a Fonte Única de Status e as correções Central ↔ Fluxo ↔ Histórico da HF4.
