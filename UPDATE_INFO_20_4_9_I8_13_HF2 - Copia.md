# AlphaFest Manager 20.4.9-I8.13-HF2 — Proveniência real do Pronto

## Objetivo
Eliminar o último falso positivo observado na Central de Entregas & Retiradas: pedidos que já estavam Pronto antes da captura confiável do timestamp apareciam como “Pronto hoje”.

## Regra definitiva
- A Central não confia apenas na existência de `pronto_em`.
- A data só entra no cálculo quando `pronto_em_confiavel = true`, marcador criado no mesmo salvamento em que uma transição real `Pronto: NÃO → SIM` é observada.
- Registro legado sem esse marcador: **Pronto · data de conclusão não registrada**.
- Novos Prontos: grava `pronto_em`, `pronto_por` e `pronto_em_confiavel` juntos.
- Ao desmarcar Pronto, os três campos auxiliares são removidos.
- `Entregue` continua implicando Pronto; se a entrega for a primeira transição que força Pronto, o carimbo é criado naquele momento.

## Histórico
Mantida a correção da HF1: entregas com data real em ordem decrescente; registros sem data real ficam no final.

## Dados
Não há migração retroativa nem invenção de datas. Os JSONs incluídos no pacote permanecem inalterados em relação à base recebida.
