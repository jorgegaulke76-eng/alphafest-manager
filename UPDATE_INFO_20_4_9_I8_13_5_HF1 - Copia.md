# 20.4.9-I8.13.5-HF1 — THU e Alpha Core na mesma fonte operacional

Correção de consistência visual identificada durante a homologação da I8.13.5.

## Corrigido
- O THU não recalcula mais `Prontos`, `Entregas hoje` e `Atrasados` com uma lista própria.
- Essas contagens passam a vir diretamente de `calcular_indicadores_unificados`, a mesma fonte da Central.
- Propostas encerradas também deixam de entrar no valor operacional aberto calculado pelo THU.
- Alpha Core, THU e Central passam a mostrar a mesma fotografia operacional para esses indicadores.

## Sem alteração de dados
Nenhum JSON operacional, status, estoque, proposta, cliente ou auditoria é migrado por esta hotfix.
