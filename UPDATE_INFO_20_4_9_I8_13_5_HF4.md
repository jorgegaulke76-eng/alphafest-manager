# 20.4.9-I8.13.5-HF4 — Materiais, Reserva e Consumo Modular

## Objetivo
Continuar a modularização da I8.13.5 sem alterar as regras de materiais já homologadas.

## Alterações
- Novo `materiais_pedido_service.py`, independente de Streamlit, Supabase e arquivos.
- O serviço concentra regras puras de:
  - consumo ativo por pedido;
  - inclusão na fila de liberação/reserva;
  - assinatura da decisão de materiais;
  - normalização dos três modos de consumo;
  - preparação da confirmação de materiais;
  - agregação de materiais manuais do pedido;
  - decisão de baixa física no início real da produção.
- `app.py` permanece responsável por leitura fresca, gravação, movimentações físicas, auditoria, timeline e mensagens de interface.
- `consumo_estoque_engine.py` continua sendo a fonte matemática de Necessário / Reservado / Consumido / Falta.

## Regras preservadas
- Ficha Técnica é receita padrão e NÃO é obrigatória globalmente.
- Cada pedido pode usar:
  1. Ficha Técnica padrão;
  2. materiais informados somente para aquele pedido;
  3. sem consumo de estoque controlado.
- Confirmar materiais cria necessidade/reserva; não baixa estoque físico.
- Baixa física ocorre somente ao iniciar produção.
- Pedido sem consumo controlado nunca inventa movimentação de estoque.
- Consumos legados já baixados permanecem idempotentes e não sofrem dupla baixa.
- Pedido não aprovado não entra na fila de liberação.
- Pronto/Entregue saem da fila de liberação de materiais.

## Segurança arquitetural
A decisão é calculada no serviço puro; a persistência e a auditoria continuam no Manager. Isso permite testes de regressão sem banco e reduz o risco de alterações futuras quebrarem reserva/consumo.

## Validação
- 41 arquivos Python validados por AST/compilação.
- 26 testes automáticos dos serviços operacionais aprovados.
- Comparação direta do documento de consumo antigo × serviço novo nos 3 modos (`ficha_padrao`, `manual_pedido`, `sem_consumo`): resultado idêntico.
- 26 JSONs operacionais preservados byte por byte em relação à HF3 homologada.
- Nenhum SQL novo e nenhum serviço pago.
