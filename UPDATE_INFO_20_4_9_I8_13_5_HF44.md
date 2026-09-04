# 20.4.9-I8.13.5-HF44 — Publicação assistida do site

## Objetivo
Reduzir o trabalho de atualização do site durante a expansão do Catálogo AlphaFest, sem transformar a marcação de produtos em publicação automática arriscada.

## Fluxo
1. Cadastrar/editar produtos no Catálogo oficial.
2. Marcar `Publicar na vitrine/site`.
3. Conferir a prévia Desktop/Celular.
4. Confirmar explicitamente e usar `🚀 Publicar site agora`.
5. O Manager envia o snapshot aprovado ao Worker `alphafest-novo` usando a API oficial de Static Assets.

## Segurança
- A marcação do produto NÃO publica sozinha.
- API Token digitado na interface não é salvo em JSON, banco, pacote ou auditoria.
- Suporta configuração segura por `Streamlit Secrets`/variáveis de ambiente para uso com um clique.
- A rotina não chama APIs de DNS, Zone, MX, Custom Domains ou Redirect Rules.
- O ZIP de produção manual continua disponível como fallback/rollback.
- README e STATUS internos do pacote não são expostos como assets públicos no deploy via API.

## Cloudflare
A publicação segue o fluxo de Direct Upload de Workers Static Assets: manifesto, upload apenas dos blobs alterados e criação/deploy de uma nova versão do Worker. `_headers` é enviado como módulo especial de Static Assets.

## Estado do domínio
- `alphafest.com.br`: produção oficial.
- `www.alphafest.com.br`: redirecionamento 301 para o domínio raiz já homologado.
