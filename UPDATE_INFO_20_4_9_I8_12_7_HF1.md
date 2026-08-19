# AlphaFest Manager 20.4.9-I8.12.7-HF1 — Comunicação da Previsão de Produção

## Objetivo
Eliminar mensagens contraditórias antes da liberação do consumo de materiais.

## Regra oficial
- Pedido aprovado, não entregue e sem consumo confirmado: **Aguardando liberação de materiais**.
- Enquanto não houver consumo confirmado, a disponibilidade física ainda **não foi apurada**.
- Nessa etapa, nenhuma tela deve informar “Sem falta física” ou “Materiais atendidos”.
- A comunicação passa a mostrar **Material ainda não apurado** e orientar: **Confirmar liberação de consumo para verificar disponibilidade dos materiais**.
- Se a entrega estiver vencida ou muito próxima, o alerta de prazo continua tendo precedência, mas a situação material permanece explicitamente não apurada.

## Fonte única
Nenhum banco ou status paralelo foi criado. A previsão continua derivada das fontes homologadas de pedidos, consumo, estoque e planejamento de compras.
