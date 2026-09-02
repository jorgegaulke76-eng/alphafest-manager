# Arquitetura Operacional — I8.13.5

## Contrato principal

**Histórico/Proposta oficial → verdade principal**

As demais áreas são projeções ou serviços derivados:

- Fluxo/Produção: espelho operacional com etapa manual.
- Risco: cálculo derivado.
- Entregas: fila derivada de Pronto/Entregue.
- Central do Dia: visão consolidada.
- Auditoria: trilha imutável de alterações confirmadas.

## Separação iniciada na I8.13.5

### `app.py`
Responsável por tela, sessão e orquestração de leitura/gravação.

### `fluxo_operacional_service.py`
Regras puras de projeção e reconciliação do Fluxo. Não conhece Streamlit nem Supabase.

### `proposal_status.py`
Fonte Única das regras Aprovado/Pago/Pronto/Entregue e encerramento.

### `consistencia_operacional_engine.py`
Compara projeções com a fonte oficial e identifica divergências.

### `status_diagnostics_service.py`
Diagnóstico puro de compatibilidade/legado de status.

### `thu_comercial_service.py` (HF14–HF15)
Inteligência comercial/financeira assistida e testável: registro explícito de envio/retorno, priorização de follow-up e cobranças assistidas de pedidos aprovados não pagos. Não envia mensagens nem altera status automaticamente; faturamento mensal permanece separado.

## Regra para próximas evoluções

Regra de negócio nova deve preferencialmente entrar em serviço/engine testável. `app.py` deve apenas coletar entrada do usuário, chamar o serviço e apresentar o resultado.
