# FestManager 9.0.0 — Base Modular Estável

## Correções
- Centraliza `STATUS_FLUXO`, `PROCESSOS_FLUXO` e `PRIORIDADES_FLUXO`.
- Corrige as referências globais da configuração da empresa no Creative Studio.
- Atualiza a identificação visível e interna para 9.0.0.

## Arquitetura
- Novo `config.py` para versão, versão dos dados, fuso e TTLs.
- Novo pacote `services/` para serviços reutilizáveis.
- Novo pacote `modules/` para extração gradual das telas.

## Segurança
- Nenhuma migração destrutiva.
- Nenhum dado de cliente, proposta, catálogo, mídia ou campanha está incluído no pacote de atualização.
