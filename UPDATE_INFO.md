# HF65.12 — Inteligência de Acesso do Site + Gráficos

## Objetivo
Transformar a tela de métricas em um painel comercial para acompanhar o site diariamente, mês a mês e ao longo dos anos.

## O que entra
- Gráfico **Dia a dia** dos últimos 30 dias: acessos, produtos abertos e cliques no WhatsApp.
- Gráfico **Mês a mês** dos últimos 12 meses.
- Gráfico **Ano** para comparação anual conforme o histórico crescer.
- Cidade, região/estado e país aproximados, obtidos pela infraestrutura Cloudflare.
- Dispositivo e navegador.
- Origem do acesso e parâmetros UTM de campanhas.
- Página de entrada da sessão.
- Cliques nas fotos da Galeria.
- Uso do filtro **Datas & Ocasiões**.
- Contexto do clique no WhatsApp, inclusive Galeria.

## Privacidade
- Não registra endereço exato.
- Localização por cidade/região é aproximada e pode variar em redes móveis ou VPN.
- Não tenta inferir faixa etária.
- O painel continua privado no Manager.

## Infraestrutura
A migração `hf65_12_site_intelligence_metrics` já foi aplicada no Supabase AlphaFest. O arquivo `SUPABASE_SITE_METRICS_HF65_12.sql` segue no pacote para auditoria/recuperação.

Versão: `20.4.9-I8.13.5-HF53.3-HF8-HF65.12`
