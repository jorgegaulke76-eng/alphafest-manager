# 20.4.9-I8.5 — THU Recorte Assistido dos Catálogos Históricos

Base: Atual 2049I841 enviada pelo usuário.

## Objetivo
Aproveitar fotos de páginas antigas sem importar a página inteira como imagem do produto.

O operador define visualmente uma área retangular e vê a prévia final antes de salvar.

## Sem dependência nova
A I8.5 usa somente Pillow + componentes nativos do Streamlit já existentes no Manager.
Não foi adicionada biblioteca externa de canvas/crop, preservando a estabilidade do deploy.

## Fluxo de recorte
Acervo Histórico:
1. escolher catálogo e página;
2. clicar em `Recortar produto desta página` ou `Recortar foto` no item;
3. ajustar:
   - faixa horizontal (esquerda → direita);
   - faixa vertical (topo → base);
4. ver:
   - página com retângulo marcado;
   - resultado do recorte;
5. confirmar destino.

Assim etiquetas de preço antigas, balões de valor, textos e outros produtos podem ficar fora da seleção.

## Produto já cadastrado
O recorte pode:
- entrar na galeria oficial;
- ser definido como primeira foto;
- ou ficar somente como referência histórica.

O produto não sofre alteração em preço, descrição, material ou campanha.

## Produto ainda não cadastrado
O recorte pode ser persistido antes do cadastro.

Ele fica no status da página como:
`Recorte pendente • Aguardando cadastro oficial`.

Ao clicar em `Preparar cadastro`, o formulário recupera esse recorte e mostra:
`Recorte preparado no Acervo Histórico`.

A opção:
`Usar este recorte como foto do produto`
vem marcada por padrão.

## Página multiproduto
Agora é possível criar um recorte diferente para cada produto da mesma página.

Exemplo:
- produto A → recorte A;
- produto B → recorte B;
- produto C → recorte C.

Nenhum deles precisa usar a página completa.

## Rastreabilidade
Cada recorte registra:
- catálogo;
- página;
- preview original;
- coordenadas reais;
- percentuais do recorte;
- usuário;
- data/hora;
- destino;
- se entrou ou não na galeria.

Campos:
- `BancoImagensHistorico`;
- `RecortesCatalogosHistoricos`;
- `recortes_pendentes` da página quando ainda não há produto oficial.

## Segurança
- página original nunca é alterada;
- nenhum preço antigo é importado;
- nenhuma quantidade mínima é criada;
- nenhum produto é criado pelo recorte;
- salvamento exige confirmação;
- recorte para novo produto é persistido antes do formulário;
- nenhuma dependência externa nova foi adicionada.
