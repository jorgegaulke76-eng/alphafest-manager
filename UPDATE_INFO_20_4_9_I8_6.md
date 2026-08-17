# 20.4.9-I8.6 — THU Saneamento do Catálogo Oficial

Base: 20.4.9-I8.5 aprovada em produção.

## Objetivo
Transformar os avisos de cadastro que já existiam no Manager em uma fila prática de saneamento,
sem criar um segundo cadastro e sem permitir correções automáticas perigosas.

## Nova aba
Catálogo → `🧹 Saneamento`

## Painel
Mostra:
- total de produtos;
- saneados;
- prioridade alta;
- revisão de legado;
- produtos sem foto;
- possíveis duplicidades.

Também calcula o `Índice de saneamento` de 0 a 100.
Esse índice mede somente integridade/revisão do cadastro.
Não representa potencial de venda, qualidade comercial ou previsão de resultado.

## Fila por prioridade
Classificação:
- 🔴 Prioridade alta: falta campo crítico ou existe forte sinal de duplicidade;
- 🟠 Revisar legado: dados antigos concatenados, descrição antiga, classificação suspeita etc.;
- 🟡 Ajuste visual: por exemplo falta de foto;
- 🟢 Saneado: nenhuma pendência detectada pelas regras atuais.

## Filtros
- prioridade;
- Material;
- Campanhas/Datas;
- Descrição;
- Valor;
- Foto;
- Categoria;
- Nome;
- Dados antigos;
- Possível duplicidade;
- pesquisa por nome/categoria/alias;
- somente produtos vinculados ao Acervo Histórico.

## Correção
Cada item possui `✏️ Corrigir cadastro`.

O botão abre o formulário oficial já existente.
O saneamento nunca cria um editor paralelo.

## Possíveis duplicidades
O Manager sinaliza apenas casos fortes:
- mesmo nome após normalização;
- nome de um produto presente como alias do outro;
- nomes equivalentes após remover palavras simples de ligação.

Nunca une, exclui ou altera produtos automaticamente.

## Acervo Histórico
A aba Saneamento mostra também o progresso das 236 páginas do Acervo:
- revisadas;
- em andamento;
- pendentes;
- institucionais.

A revisão de página histórica e o saneamento do produto oficial permanecem controles separados.

## Segurança
Nenhuma rotina desta versão:
- altera preço;
- preenche material;
- reescreve descrição;
- autoriza campanha;
- exclui produto;
- une duplicidade;
- cria quantidade mínima;
- modifica histórico de orçamento.

Toda alteração exige abertura e salvamento do cadastro oficial.
