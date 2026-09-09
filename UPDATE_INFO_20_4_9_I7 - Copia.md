# 20.4.9-I7 — THU Inteligência de Marketing e Resultados

Base: Atual 2049I6 aprovada.

## Objetivo
Cruzar Marketing e atividade comercial do AlphaFest Manager sem confundir correlação com causalidade.

A I7 responde principalmente:
- o que tem demanda e pouca divulgação;
- o que está sendo muito divulgado e gera pouca atividade de propostas no Manager;
- quais produtos possuem propostas pagas mesmo com baixa exposição social;
- como a atividade de propostas se comportou antes/depois de uma publicação;
- quais propostas vieram de atendimentos iniciados em Instagram/Facebook;
- onde faltam dados para confiar na análise.

## Novo painel
Marketing:
`📊 Assistente THU • Inteligência de Marketing e Resultados`

A análise é executada sob demanda para não pesar os demais fluxos.

Períodos:
- 30 dias;
- 60 dias;
- 90 dias;
- 120 dias;
- 180 dias.

O período atual é comparado com o período imediatamente anterior de mesma duração.

## Fonte comercial
A I7 usa o histórico oficial de propostas e as mesmas regras existentes para:
- proposta encerrada;
- aprovado;
- pago;
- cálculo do valor total.

Produtos são consolidados pelo nome oficial + aliases do Catálogo.

## Valores por produto
Para não inventar rateio:
- valor por produto = quantidade × valor unitário;
- é chamado explicitamente de `valor bruto dos itens`;
- desconto e taxa de entrega continuam pertencendo à proposta inteira;
- eles não são distribuídos artificialmente entre produtos.

## Visão geral
Mostra:
- publicações registradas;
- propostas criadas;
- propostas atualmente aprovadas;
- propostas atualmente pagas;
- valor orçado;
- valor aprovado atual;
- valor recebido atual;
- aprovação atual da coorte.

Observação:
`valor recebido atual` significa propostas criadas no período que hoje estão pagas.
Não é caixa organizado pela data do pagamento.

## Produto × Divulgação
Para cada produto:
- propostas;
- aprovadas;
- pagas;
- quantidade orçada;
- quantidade paga;
- valor bruto dos itens orçados;
- valor bruto dos itens em propostas pagas;
- número de publicações;
- canais;
- última publicação;
- evidência direta de origem social quando existir.

Sinais possíveis:
- Divulgar mais;
- Venda com pouca divulgação;
- Revisar divulgação;
- Revisar frequência/mensagem;
- Monitorar.

Os sinais usam posição relativa de demanda × exposição e regras mínimas de volume.
São recomendações de gestão, não provas de eficiência/ineficiência de campanha.

## Levar ao THU
Produtos com oportunidade de divulgação podem ser enviados ao fluxo oficial do THU para consulta do Catálogo e preparação de campanha.

## Evidência direta: origem do atendimento
A I7 cruza `atendimento_id` da proposta com:
- canal_origem;
- origem;
- canal.

Quando o atendimento começou no Instagram/Facebook:
- a proposta recebe evidência direta do canal de entrada;
- o produto mostra quantas propostas possuem essa origem.

Isso ainda não identifica qual post específico gerou o contato.

## Sinais temporais
Para evitar janelas incompletas:
- usa a última publicação do produto que já tenha pelo menos 14 dias completos após ela;
- compara propostas do mesmo produto nos 14 dias anteriores;
- compara com os 14 dias posteriores;
- mostra diferença absoluta.

A interface declara explicitamente:
`associação temporal não demonstra que a publicação causou a mudança`.

## Qualidade dos dados
Mostra:
- percentual de publicações vinculadas a produto;
- percentual de itens das propostas reconhecidos no Catálogo;
- percentual de propostas com origem de atendimento identificada;
- posts sem produto;
- posts com produto fora do Catálogo;
- itens das propostas ainda sem correspondência segura no Catálogo.

## Cache / consistência
A análise I7 é invalidada automaticamente quando mudam:
- propostas;
- Marketing / Acervo Social;
- Catálogo.

## Segurança analítica
A I7 nunca afirma:
- que uma postagem causou uma venda;
- que curtida equivale a venda;
- que correlação temporal é atribuição;
- que um produto divulgado sem proposta é um fracasso.

O sistema usa as expressões:
- sinal;
- atividade registrada;
- associação temporal;
- evidência de canal de origem;
- oportunidade para revisão.
