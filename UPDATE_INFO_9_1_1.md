# FestManager 9.1.1 — Mídia do Catálogo e Alpha Connect

## Correções

- Imagens do catálogo agora podem ser processadas quando estão salvas como:
  - URL pública ou assinada (HTTP/HTTPS);
  - caminho local ou relativo;
  - bytes/upload do Streamlit;
  - data URL em Base64.
- O Creative Studio passa a baixar os bytes reais da imagem antes de gerar PNG e previews.
- O upload livre continua isolado do catálogo.

## Nova área

Em **Configurações → Alpha Connect**, o sistema mostra o estado básico das integrações sem revelar chaves:

- OpenAI;
- Meta/Facebook;
- Instagram;
- WhatsApp Business;
- YouTube;
- TikTok.

O diagnóstico indica credenciais configuradas, incompletas ou ausentes. A publicação real ainda depende da conclusão do OAuth e dos testes de cada plataforma.

## Segurança

- Nenhum segredo é exibido.
- Nenhum dado operacional foi incluído ou alterado no pacote.
- A versão dos dados permanece 5; não há migração destrutiva.
