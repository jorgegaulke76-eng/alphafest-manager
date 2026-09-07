# 20.4.9-I8.13.5-HF52.1 — Métricas privadas do Site

## Objetivo
Dar ao administrador uma visão simples e privada do desempenho comercial do site sem exibir contadores ao público.

## Primeira versão
- acessos ao site (24h, 7d e 30d);
- produtos abertos;
- cliques no WhatsApp;
- sessões e visitantes estimados;
- ranking dos produtos mais abertos;
- ranking dos produtos que mais levaram ao WhatsApp.

## Privacidade e segurança
- o painel fica dentro da Central do Site e só aparece para perfil técnico/administrador;
- visitante público só possui permissão de INSERT na tabela dedicada;
- não existe SELECT público;
- o Manager lê os dados somente com SUPABASE_SERVICE_KEY;
- prévias internas do Manager não contam como acesso;
- não são coletados nome, telefone, e-mail ou conteúdo de conversa.

## Instalação única
Execute `SUPABASE_SITE_METRICS_HF52_1.sql` uma única vez no SQL Editor do Supabase.
É necessário manter `SUPABASE_URL`, `SUPABASE_KEY` (publishable/anon) e `SUPABASE_SERVICE_KEY` configurados nos Secrets do Manager.

Nada é publicado automaticamente. O HF44 continua controlando a publicação do site.
