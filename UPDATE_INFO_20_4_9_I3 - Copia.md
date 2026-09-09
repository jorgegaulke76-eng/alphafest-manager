# 20.4.9-I3 — THU Acervo do Site AlphaFest

Base: Atual 2049I21 aprovada.

## Objetivo
Transformar o site público antigo da AlphaFest em acervo assistido para o Manager, sem transformar o site em fonte oficial.

A fonte oficial continua sendo:
- Catálogo para produto, preço, material, descrição e elegibilidade;
- Biblioteca para artes aprovadas;
- Calendário para datas/oportunidades.

## Novo painel
Em Marketing > Central de Campanhas:
`🌐 THU • Acervo do Site AlphaFest`

A análise só acontece quando o usuário clicar em `Analisar o site agora`.

## Auditoria Site × Catálogo
O THU:
- lê apenas páginas públicas de alphafest.com.br;
- descobre páginas a partir do menu público;
- limita a quantidade de páginas por análise;
- compara os nomes encontrados com nome oficial + aliases do Catálogo;
- separa correspondências oficiais, possíveis correspondências e possíveis ausências;
- mostra quantos produtos do Catálogo não tiveram correspondência nas páginas analisadas;
- nunca cria ou mescla produtos automaticamente.

## Acervo de fotos
Páginas com imagens podem ser revisadas visualmente.
Para importar, o usuário precisa:
1. escolher o produto oficial;
2. selecionar individualmente as imagens;
3. escolher como salvar;
4. confirmar a importação.

Opções:
- Adicionar como referências históricas;
- Adicionar e usar a primeira como foto principal;
- Salvar como variação histórica.

As imagens aprovadas usam o mesmo armazenamento do Catálogo.

## Rastreabilidade
Cada importação registra:
- origem `Site AlphaFest legado`;
- URL da página;
- título da página;
- URLs de origem das imagens;
- ação;
- observação;
- data;
- usuário.

O produto também recebe `FontesHistoricas`.

## Campanhas históricas
O painel identifica páginas de datas/campanhas do site.
- Se a campanha já existe em CampanhasPermitidas, o sistema informa;
- se não existe, ela é mostrada como campanha histórica para revisão;
- nenhuma campanha é adicionada automaticamente;
- há atalho para o Calendário Comercial.

## Segurança e desempenho
- domínio de páginas limitado a alphafest.com.br;
- imagens limitadas ao domínio AlphaFest / armazenamento Wix;
- análise sob demanda;
- limite configurável de páginas;
- leitura paralela com número reduzido de conexões;
- timeout por página;
- HTML limitado a 4 MB;
- imagens importadas limitadas a 15 MB;
- somente PNG/JPG/WEBP são aceitos;
- nenhum conteúdo do site sobrescreve dados oficiais automaticamente.
