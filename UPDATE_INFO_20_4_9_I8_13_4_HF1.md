# AlphaFest Manager 20.4.9-I8.13.4-HF1

Hotfix de homologação da Auditoria e Linha do Tempo Oficial.

## Correção
- O Histórico de propostas ainda exibia apenas a timeline legada (`timeline` da proposta), embora a auditoria central já estivesse sendo gravada corretamente.
- O bloco antigo foi substituído pela `Linha do tempo oficial` já usada no fluxo de atualização rápida.
- Eventos da auditoria central aparecem primeiro com data/hora, usuário, ação, campo e `valor anterior → valor novo`.
- Eventos históricos antigos permanecem preservados abaixo, no mesmo bloco.
- Nenhum status, estoque, proposta ou JSON operacional é migrado/alterado por esta hotfix.
