# FestManager 11.1.0 — Central de Oportunidades e Fonte da Venda

## Operação protegida
- A nova Central de Oportunidades foi criada em módulo isolado (`central_oportunidades.py`).
- Uma falha no módulo não impede a Caixa Unificada, orçamentos ou demais áreas de abrirem.
- Nenhuma migração destrutiva foi adicionada; registros antigos continuam válidos.

## Central de Oportunidades
- Fila exclusiva para contatos captados por Instagram, Facebook, TikTok, YouTube, site, Google, indicação e loja física.
- Identificação clara do canal de origem.
- Fluxo orientado para migrar o atendimento comercial ao WhatsApp.
- Estados: Nova captação, convite enviado, aguardando migração, migrou, atendimento no WhatsApp, orçamento, venda, não migrou, descartada, recusada, duplicada e spam.
- Ações rápidas para convite, confirmação de migração, descarte, recusa, orçamento e venda.

## Fonte da venda
- Canal de origem e canal de atendimento separados.
- Tipo de conteúdo, nome do post/Reel/vídeo, link, campanha, produto relacionado e motivo do contato.
- A origem permanece preservada mesmo quando o atendimento passa ao WhatsApp.

## Indicadores
- Contatos, migrações ao WhatsApp, orçamentos, vendas, conversão e faturamento por canal.
- Ranking dos conteúdos que geraram contatos, orçamentos e vendas.
- Cruzamento seguro com propostas que possuem `atendimento_id`.

## Configuração recomendada
No Streamlit Secrets, opcionalmente informe o número público da Alphafest para gerar o link de migração:

```toml
WHATSAPP_PUBLIC_NUMBER = "5511999999999"
```
