# FestManager 5.4.0 — Assistente Operacional

## Base
- Versão anterior: 5.3.0
- Nova versão: 5.4.0
- Versão dos dados: permanece 3
- Migração: não necessária

## Arquivos alterados
- `app.py`
- `VERSAO.txt`
- `CHANGELOG.md`
- `UPDATE_INFO.md`

## O que mudou
- Nova seção **Assistente operacional** na Central do Dia.
- As cinco prioridades mais importantes são ordenadas por SLA, prazo e etapa da operação.
- Atendimentos com telefone ganham atalho direto para o WhatsApp.
- Cartão do cliente passa a mostrar ticket médio, última proposta, itens mais solicitados, temas recorrentes e próxima ação sugerida.
- As novas informações são calculadas a partir dos registros existentes; nenhum cadastro é modificado.

## Segurança
- Nenhum arquivo de dados faz parte do pacote.
- Clientes, catálogo, fotos, propostas, projetos e campanhas permanecem no Supabase.
- Não há migração de banco nesta versão.
