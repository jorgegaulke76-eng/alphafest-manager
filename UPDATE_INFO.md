# FestManager 5.6.0 — Central Multicanal

Base anterior: 5.5.0

## Incluído
- Caixa unificada por canal: WhatsApp, Instagram, Facebook, Site/Catálogo e atendimento manual.
- Filtro e identificação visual do canal de origem.
- Tela de configuração das integrações oficiais Meta.
- Teste de entrada multicanal sem depender das credenciais da Meta.
- Edge Function do Supabase pronta para receber webhooks da Meta e registrar oportunidades no documento `atendimentos_db`.
- Deduplicação por identificador externo de mensagem.

## Importante
A atualização prepara toda a estrutura, mas os canais só passam a receber mensagens reais após configurar as credenciais e publicar o webhook conforme `META_INTEGRACAO.md`.

Migração destrutiva: não.
Arquivos de dados substituídos: não.
