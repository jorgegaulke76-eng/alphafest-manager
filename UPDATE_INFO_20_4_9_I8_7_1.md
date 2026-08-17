# 20.4.9-I8.7.1 — Homologação e Blindagem do Gerador de Catálogos

Base exclusiva: 20.4.9-I8.7 (`Atual 2049I87.zip`).

## Objetivo
Homologar o Gerador de Catálogos antes da I8.8 — Central de Catálogos, preservando todos os módulos já aprovados e mantendo o Catálogo Oficial como única fonte de verdade.

## Correções e blindagens
- Categorias equivalentes por identidade (ex.: `BUBBLE` e `Bubble`) são unificadas somente na apresentação do gerador/HTML.
- Nenhum nome de categoria é regravado no Catálogo Oficial.
- Seleção de produtos passou a usar o índice real do registro, evitando confusão quando existem produtos com o mesmo nome.
- Campos `Imagens`, `Variacoes` e `CampanhasPermitidas` aceitam com segurança lista ou texto único no gerador.
- Navegação do HTML usa âncoras estáveis com sufixo de identidade, reduzindo risco de colisões.
- WhatsApp usa `whatsapp_catalogo` e possui fallback seguro para `celular` caso a configuração dedicada esteja vazia.
- Imagens remotas recebem carregamento tardio (`loading=lazy`) para melhorar abertura de catálogos maiores.
- Métricas da tela foram separadas em selecionados, produtos no arquivo, sem foto no arquivo e sem preço atual.
- Produtos sem foto excluídos da saída continuam intactos no Catálogo Oficial.
- Produtos sem preço continuam exibindo `Preço sob consulta`; nenhum preço histórico ou estimado é utilizado.

## Segurança comercial preservada
- Gerador continua 100% somente leitura.
- Sem criação ou edição de produtos.
- Sem alteração de preço.
- Sem alteração de campanha.
- Sem alteração de foto.
- Sem alteração de saneamento.
- Sem quantidade mínima inventada.
- Aba antiga `Catálogo para cliente` preservada como fallback.

## Homologação técnica executada
- Compilação de todos os arquivos Python.
- Teste do motor com categorias `BUBBLE`/`Bubble`.
- Teste de produto sem preço.
- Teste de produto sem foto.
- Teste de campo de imagem como texto único.
- Teste de variação como texto único.
- Teste de ocultação de preço e WhatsApp.
- Teste de escape de conteúdo HTML.

## Próximo marco aprovado
Após homologação humana da I8.7.1, iniciar **20.4.9-I8.8 — Central de Catálogos AlphaFest**.
