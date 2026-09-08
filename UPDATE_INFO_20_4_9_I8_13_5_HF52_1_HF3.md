# 20.4.9-I8.13.5-HF52.1-HF3 — Origem dos acessos + termos buscados

## Objetivo
Evoluir o painel privado de métricas para mostrar de onde o visitante chegou e o que procura dentro do site.

## Entregas
- preserva Hoje / 7 dias / 30 dias e o funil comercial;
- preserva atualização automática a cada 30 segundos e Atualizar agora;
- novo ranking **Origem dos acessos · 30 dias**;
- novo ranking **Termos mais buscados no site · 30 dias**;
- busca registrada após 900 ms sem digitação e a partir de 2 caracteres, evitando registrar cada tecla;
- nenhuma informação pessoal, telefone, nome de cliente ou conversa é coletada;
- a prévia interna continua fora da contagem.

## Ativação
Antes de publicar esta versão, execute uma única vez `SUPABASE_SITE_METRICS_HF52_1_HF3.sql` no SQL Editor do Supabase. Ele apenas permite o novo tipo de evento `search` na tabela já existente.

## Compatibilidade
Não altera Catálogo, Galeria, visual homologado, preços, WhatsApp, HF44 ou demais rotinas do Manager.
