# AlphaFest Manager 20.4.9-I8.13.5

## Modularização e fortalecimento da arquitetura — Fase 1

Base: **20.4.9-I8.13.4-HF7 homologada**.

Esta versão não adiciona regras comerciais nem altera dados operacionais. O foco é reduzir risco de regressão ao continuar evoluindo o Manager.

### Mudanças

- Criado `fluxo_operacional_service.py`:
  - inferência de processos;
  - status inicial do Fluxo;
  - normalização de etapas legadas;
  - projeção/reconciliação Histórico oficial → Fluxo;
  - preservação de etapa manual, prioridade e campos operacionais.
- Criado `status_diagnostics_service.py` para retirar do `app.py` o diagnóstico puro da Fonte Única de Status.
- `app.py` passa a atuar mais como orquestrador/tela e chama o serviço puro para reconciliar o Fluxo.
- Mantido o contrato: **Histórico/Proposta é a verdade oficial; `producao_db` é apenas espelho operacional/manual**.
- Corrigida compatibilidade de `adicionar_evento_timeline` para aceitar usuário opcional sem quebrar chamadas antigas.
- Criados testes de regressão em `tests/test_operational_services.py`, usando apenas `unittest` da biblioteca padrão (custo zero / sem dependência nova).

### O que NÃO mudou

- Aprovado → Pago → Pronto → Entregue.
- Saneamento histórico HF7.
- Auditoria de sincronização.
- Reserva/consumo de materiais.
- Central do Dia, Fluxo, Histórico, Risco e Entregas.
- Estrutura dos JSONs operacionais.
- Supabase / credenciais / SQL.

### Validação prevista

1. Compilação/AST de todos os arquivos Python.
2. Testes unitários dos serviços operacionais.
3. Comparação byte a byte dos JSONs com a HF7 base.
4. Smoke test de inicialização do Streamlit.
5. Integridade do ZIP final.
