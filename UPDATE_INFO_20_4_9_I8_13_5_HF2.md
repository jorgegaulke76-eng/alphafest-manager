# 20.4.9-I8.13.5-HF2 — Auditoria e Sincronização modular

Base: 20.4.9-I8.13.5-HF1 homologada.

## Objetivo
Reduzir o acoplamento do `app.py` sem alterar a operação homologada.

## Alterações
- Novo `auditoria_operacional_service.py`, sem dependência de Streamlit/Supabase.
- Execução da Auditoria de Sincronização passou a delegar o cálculo ao serviço modular.
- Aplicação do Saneamento Histórico Seguro passou a delegar o loop transacional ao serviço.
- Preparação das linhas de prévia/sincronização saiu da UI.
- `app.py` permanece responsável por sessão, leitura/gravação e renderização.
- Mesmas regras da HF7/HF1: Histórico é fonte oficial; Fluxo é espelho; Risco/Entregas são projeções; saneamento nunca inventa Pago, nunca desfaz status e só audita após confirmação da gravação.

## Regressão
- Testes do Fluxo preservados.
- Teste THU/Alpha Core preservado.
- Novos testes para auditoria modular, reparos e saneamento transacional.
