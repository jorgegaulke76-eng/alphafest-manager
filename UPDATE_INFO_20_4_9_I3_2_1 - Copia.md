# 20.4.9-I3.2.1 — Preview HD + Auditoria de Resolução

Base: 20.4.9-I3.2.

## Correção
A I3.2 já tentava baixar o original na importação, mas o modal ainda exibia a miniatura reduzida.
A I3.2.1 corrige essa diferença.

## Modal
- prévia usa `original_url` quando disponível;
- miniatura antiga só é fallback;
- informa quando a prévia exibida é a versão original.

## Importação
- solicita JPEG/PNG/WEBP para evitar retorno AVIF incompatível;
- continua tentando arquivo original primeiro;
- miniatura continua como fallback;
- mede largura e altura reais do arquivo baixado com Pillow;
- registra largura, altura e bytes importados na origem da imagem.

## Qualidade
Se o maior lado do arquivo original tiver menos de 900 px:
- a foto ainda pode ser salva;
- o THU avisa que o arquivo original do site já é pequeno;
- nenhum upscale artificial é realizado.

## Desempenho
As listagens continuam usando miniaturas pequenas para não deixar o Marketing pesado.
Somente o modal de revisão carrega a imagem de maior resolução.
