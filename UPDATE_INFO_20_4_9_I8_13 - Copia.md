# AlphaFest Manager 20.4.9-I8.13 — Central de Entregas & Retiradas

## Objetivo
Fechar o ciclo operacional criado pela I8.12.8-HF2: **Pronto → saída → Entregue**, sem criar uma fonte paralela de status.

## Central de Entregas & Retiradas
- Novo módulo em **Operação → Entregas & Retiradas**, inicialmente liberado para homologação no perfil Jorge.
- A fila contém exclusivamente propostas oficialmente **Pronto = SIM** e **Entregue = NÃO**.
- Indicadores: prontos aguardando saída, previstos para hoje, clientes ainda não registrados como avisados, aguardando há 3+ dias e pagamento pendente.
- Pesquisa por proposta, cliente ou produto e filtros operacionais por aviso, data, forma de saída e pagamento.

## Logística ligada à proposta oficial
Sem banco novo. A proposta pode receber apenas metadados auxiliares:
- `logistica_tipo`: Retirada na AlphaFest / Entrega AlphaFest / Motoboy / Outro.
- `logistica_observacao`: orientação operacional curta.
- `cliente_avisado_em` e `cliente_avisado_por`: registro auditável do aviso ao cliente.

Esses campos não substituem **Pronto** nem **Entregue**.

## Ações rápidas
- Salvar forma de saída e observação.
- Abrir WhatsApp com mensagem de pedido pronto.
- Registrar que o cliente foi avisado, com data/hora/usuário e timeline da proposta.
- Marcar **Entregue** com confirmação explícita. A regra da HF2 continua valendo: Entregue implica Pronto e remove o pedido das filas operacionais abertas.

## Central do Jorge
- Novo atalho **Entregas** nas ações rápidas.
- Novo resumo: quantos pedidos estão prontos, quantos são de hoje, quantos ainda não foram avisados e quantos aguardam há 3+ dias.
- Botão direto para abrir a Central de Entregas & Retiradas.

## Compatibilidade
- Nenhum JSON operacional é migrado ou regravado pela atualização.
- Pedidos antigos continuam compatíveis; ausência dos novos metadados significa apenas logística ainda não registrada.
- A I8.12.8-HF2 permanece como fonte oficial de Pronto/Entregue e de sincronização com Produção.
