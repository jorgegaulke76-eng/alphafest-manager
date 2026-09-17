# AlphaFest Manager — HF65.9

Versão: `20.4.9-I8.13.5-HF53.3-HF8-HF65.9`

## Objetivo
Transformar as fotos reais da Galeria em uma vitrine temática por **Datas & Ocasiões**, acessível diretamente pelo campo de Categorias do site através do cartão 🎈.

## O que muda
- Galeria interna ganha seleção múltipla **🎈 Datas & Ocasiões** no registro de novos trabalhos.
- Trabalhos já existentes ganham editor próprio de Datas & Ocasiões.
- O acervo interno pode ser filtrado por Data/Ocasião.
- A Galeria pública ganha o filtro **🎈 Datas & Ocasiões**.
- O site passa a exibir, junto aos cartões de Categorias, o cartão **🎈 Datas & Ocasiões**.
- Ao escolher uma ocasião, o visitante vê as fotos reais da Galeria marcadas com aquela ocasião.

## Compatibilidade
O campo antigo `ocasiao` continua válido e é lido junto com o novo campo `datas_ocasioes`. Não há migração destrutiva nem duplicação de cadastro.

## Segurança
Nenhum arquivo privado da Galeria é exposto diretamente. A publicação continua usando o fluxo já homologado de resolução das imagens autorizadas.
