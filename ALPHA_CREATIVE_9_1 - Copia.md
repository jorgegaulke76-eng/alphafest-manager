# FestManager 9.1.0 — Alpha Creative Studio Premium

## Upload livre

O modo **Upload livre** não lê nem reaproveita nome, descrição, preço ou categoria do catálogo. Para evitar campanhas incompatíveis com a foto, informe o nome do produto/serviço e descreva o que aparece na imagem.

## IA comercial

O Studio usa a OpenAI quando a chave `OPENAI_API_KEY` estiver configurada nos Secrets do Streamlit. A geração é feita em uma única chamada para todos os canais selecionados e pode analisar a imagem enviada. O modelo pode ser alterado pelo segredo ou variável `OPENAI_MODEL`; o padrão é `gpt-5-mini`.

Sem chave de API, o sistema continua funcionando com o gerador comercial local e identifica isso no registro da campanha.

Exemplo de Secrets:

```toml
OPENAI_API_KEY = "sua-chave"
OPENAI_MODEL = "gpt-5-mini"
```

## Artes e identidade

As entradas podem ser PNG, JPG, JPEG, WEBP, BMP ou TIFF. As artes finais de imagem são sempre exportadas em **PNG**, no tamanho do canal. O logotipo da Alphafest e uma assinatura discreta são aplicados automaticamente.

## Vídeos

É possível anexar e preservar MP4, MOV, M4V, AVI, MKV ou WEBM para Reels, TikTok e Shorts. Nesta versão, o vídeo original e os roteiros são organizados na campanha; o processamento automático das versões MP4 entra no Video Studio.

## Aprovação e publicação em lote

Cada canal continua sendo aprovado individualmente. O botão de lote envia todos os canais aprovados, em uma única ação, para a fila de publicação. A postagem automática nas redes depende da conexão das credenciais oficiais de Instagram, Facebook, WhatsApp, TikTok e YouTube.
