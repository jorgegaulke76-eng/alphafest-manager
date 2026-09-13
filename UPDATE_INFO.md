# AlphaFest Manager — HF60

## Correção da conexão Cloudflare na Central do Site

Atualização incremental sobre a HF59. Corrige somente o fluxo de publicação do site após a simplificação da Central.

### Correção
- a HF59 podia considerar a Cloudflare “pronta” apenas porque havia valores não vazios em Secrets/ambiente, mesmo quando o **Account ID** estava malformado;
- o botão de publicação agora só é liberado quando o Account ID tem formato válido;
- adiciona o expander compacto **Ajustar conexão Cloudflare**, sem voltar com a confusão das telas antigas;
- o **Account ID** pode ser corrigido diretamente na tela;
- se o API Token já estiver em configuração segura, ele continua oculto e não precisa ser digitado novamente;
- mantém o botão **Testar conexão sem publicar**;
- a publicação continua apontando somente para o Worker `alphafest-novo` e não altera DNS, domínio, MX ou webmail.

### Preservado
- HF59 — Central do Site simplificada + produtos em múltiplas categorias;
- HF58 — Galeria em múltiplas categorias;
- HF57 — categorias do site sem limite;
- HF56 — lightbox da Galeria pública;
- HF55 — exclusão individual de foto;
- HF54 e demais funções homologadas;
- Template Mestre HF7 congelado e Template Anna homologado.
