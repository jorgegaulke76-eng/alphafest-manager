# 20.4.9-I8.6.1 — THU Saneamento com Confirmação Humana

Base: 20.4.9-I8.6.

## Objetivo
Evitar que alertas legítimos reapareçam para sempre depois que Jorge/Anna já revisaram e confirmaram conscientemente a decisão.

## Nova ação
Na aba:
Catálogo → 🧹 Saneamento

Cada produto com pendência possui:
`✅ Revisar / aceitar`

A revisão abre um diálogo específico para o alerta selecionado.

## Campanhas/Datas
Se o produto pode ser divulgado durante todo o ano:
`🌐 Definir Permanente / Todas as épocas`

Isso grava oficialmente:
`Permanente / Todas as épocas`
em `CampanhasPermitidas`.

Não é uma exceção escondida: é a própria elegibilidade oficial do produto.

## Material
Material continua obrigatório para produtos físicos.

Somente quando o cadastro realmente representar serviço/situação em que material não se aplica, é possível registrar:
`Material não se aplica`

Exige justificativa.
O campo:
`MaterialNaoSeAplicaTHU`
fica registrado no produto.

## Foto
Foto é tratada como ajuste visual.
É possível registrar temporariamente:
`Revisado — manter sem foto`

Exige justificativa.
A decisão pode ser reaberta depois.

## Alertas de legado
Alertas como:
- nome e categoria idênticos;
- descrição muito longa;
- material concatenado;
- referência de imagem local antiga;

podem ser:
`Revisado e aceito como está`

sempre com justificativa.

A aceitação do alerta de legado fica vinculada ao conteúdo revisado.
Se o conteúdo mudar posteriormente, o alerta pode reaparecer automaticamente para nova conferência.

## Possíveis duplicidades
Quando dois produtos parecem duplicados, mas são realmente diferentes:
`Confirmar que são produtos diferentes`

Exige justificativa e registra a decisão nos dois produtos.

O par deixa de voltar como duplicidade enquanto essa decisão permanecer válida.

## Histórico e auditoria
Campo:
`RevisoesSaneamentoTHU`

Cada decisão registra:
- chave do alerta;
- tipo;
- texto;
- decisão;
- justificativa;
- usuário;
- data/hora;
- versão da regra.

Nenhuma decisão antiga é apagada.

## Reabrir decisão
As decisões humanas ativas aparecem dentro da revisão.
É possível:
`↩️ Reabrir este alerta`

A reabertura também é registrada no histórico.

## Segurança
A confirmação humana NÃO permite esconder silenciosamente campos estruturais como:
- Nome;
- Categoria;
- Descrição;
- Valor.

Esses continuam exigindo correção no Cadastro Oficial.

Nenhuma rotina desta versão:
- inventa preço;
- importa preço histórico;
- cria quantidade mínima;
- altera orçamento;
- apaga produto;
- une produtos automaticamente;
- modifica campanhas sem confirmação explícita.
