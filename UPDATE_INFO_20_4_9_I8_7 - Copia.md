# 20.4.9-I8.7 — Gerador de Catálogos AlphaFest

Base oficial: 20.4.9-I8.6.1.

## Princípio da entrega
A I8.7 entra de forma aditiva e somente leitura sobre o Catálogo Oficial.
Nenhum produto, preço, foto, campanha, saneamento ou histórico é alterado pelo gerador.

A aba anterior `Catálogo para cliente` foi mantida integralmente como fallback.

## Nova aba
Catálogo → `✨ Gerador I8.7`

## Seleção
O gerador permite:
- selecionar categorias;
- filtrar por campanha/data oficial;
- selecionar produtos individualmente;
- considerar automaticamente `Permanente / Todas as épocas` quando uma campanha específica é escolhida.

Somente produtos ativos entram na base do gerador.

## Conteúdo exibido
É possível ligar/desligar:
- preços;
- descrição;
- material;
- botão de WhatsApp;
- produtos sem foto.

Também é possível definir:
- título;
- subtítulo;
- observação opcional no rodapé.

## Segurança comercial
- preço vem exclusivamente do campo oficial `Preco`;
- preço ausente aparece como `Preço sob consulta` quando preços estiverem habilitados;
- nenhum valor é inventado;
- nenhuma regra de quantidade mínima é criada ou exibida;
- nenhuma informação histórica de preço é usada;
- o filtro de campanha apenas lê `CampanhasPermitidas`.

## Qualidade antes da exportação
A tela mostra:
- quantidade de produtos no arquivo;
- quantidade selecionada sem foto;
- quantidade sem preço atual.

Produtos sem foto podem ser excluídos do arquivo ou exibidos com um espaço neutro `Imagem em preparação`.

## Saída
A primeira saída da I8.7 é HTML responsivo:
- celular;
- computador;
- navegação por categoria;
- cards comerciais;
- identidade visual AlphaFest;
- estilo próprio de impressão;
- WhatsApp por produto quando habilitado.

Não foi adicionada nova dependência ao projeto.
