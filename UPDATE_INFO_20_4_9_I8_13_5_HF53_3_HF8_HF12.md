# 20.4.9-I8.13.5-HF53.3-HF8-HF12

Base: **20.4.9-I8.13.5-HF53.3-HF8-HF11**.

## Correção
- Corrige a identificação de origem das campanhas do Template Anna.
- O Manager HF11 renderizava com o Template Anna HF11, mas `app.py` ainda gravava `HF53.3-HF8-HF10` em `origem_criativa` e `designer_rules_version`.
- A origem passa a acompanhar automaticamente `template_versao` para `anna_social_redes`.
- Registros Anna cuja `template_versao` já é HF11 e foram rotulados como HF10 são normalizados em leitura para HF11.
- O renderer do Template Anna permanece **HF53.3-HF8-HF11**.
- O Template Mestre Comercial **HF53.2-HF5-HF7 permanece congelado e sem alteração**.
