# 20.4.9-I3.2 — Imagens Originais do Acervo

Base: 20.4.9-I3.1.

## Correção principal
O site Wix frequentemente entrega miniaturas/redimensionamentos em URLs `/v1/fill/...`.
A I3.2 passa a:
- preferir a maior imagem disponível em `srcset`;
- reconhecer URLs transformadas do Wix;
- reconstruir a URL do arquivo original em `static.wixstatic.com/media/...`;
- tentar o original primeiro e usar a miniatura apenas como fallback;
- aumentar o limite de importação de imagem para 25 MB;
- registrar URL de preview, URL original e bytes efetivamente importados.

## Importante
O sistema não faz upscale artificial.
Se o arquivo original do site já for pequeno, ele continuará pequeno.
A melhoria serve para evitar salvar uma miniatura quando existe um original maior.

## Compatibilidade
Scans anteriores da I3/I3.1 são reprocessados e passam a receber `original_url` quando possível.

## Segurança
- apenas URLs de imagem autorizadas do domínio AlphaFest/Wix;
- apenas PNG/JPG/WEBP;
- nenhuma foto é importada sem confirmação;
- fallback automático para a URL antiga caso o original não esteja acessível.
