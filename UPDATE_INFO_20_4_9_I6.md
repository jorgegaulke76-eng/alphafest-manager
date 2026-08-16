# 20.4.9-I6 — THU Acervo Social + Histórico de Publicações

Base: Atual 2049I5 aprovada.

## Objetivo
Fechar o ciclo de Marketing:
Preparada → Publicada → Histórico.

A I6 cria uma memória social confiável sem depender, nesta etapa, de scraping contínuo de Instagram/Facebook.

## Acervo Social
Novo painel em Marketing:
`📱 Assistente THU • Acervo Social + Histórico de Publicações`

Inclui atalhos para:
- Instagram AlphaFest;
- Facebook AlphaFest.

## Registro de publicação
Origens:
- Campanha preparada pelo THU;
- Publicação histórica;
- Publicação avulsa.

Campos:
- canal;
- data;
- tipo de mídia;
- produto oficial;
- campanha;
- legenda/texto;
- link;
- observação;
- imagem/print opcional.

Canais:
- Instagram Feed;
- Instagram Story;
- Instagram Reel;
- Instagram Carrossel;
- Facebook;
- Status WhatsApp.

## Campanhas preparadas
Quando o registro vem de campanha preparada:
- produto, campanha, arte e texto são reaproveitados;
- Story/Status usa o texto curto;
- Feed/Reel usa a legenda;
- o registro fica vinculado à campanha preparada;
- o status passa a `Publicada`.

## Réplica Facebook
Se a configuração `Replicação no Facebook pela Meta` estiver ativa e o canal for Instagram Feed:
- o sistema oferece registrar também a réplica;
- a opção começa desmarcada;
- só registra se o usuário confirmar que a réplica realmente aconteceu.

## Histórico social
Cada registro possui:
- ID;
- origem;
- canal;
- tipo de mídia;
- data da publicação;
- produto;
- campanha;
- arte;
- legenda;
- link;
- observação;
- imagem/print;
- campanha preparada relacionada;
- data/hora de registro;
- usuário.

Erros não são apagados: podem ser anulados, preservando auditoria.

## Memória por produto
O THU mostra:
- quantidade de publicações;
- data da última publicação;
- dias sem publicar;
- canais já utilizados.

## Repetição recente
Antes de registrar:
- mesmo produto no mesmo canal em até 14 dias gera alerta;
- mesma arte em até 30 dias gera alerta.

O alerta não bloqueia a decisão.

## Integração com Plano Executivo I5
O plano agora distingue:
- Campanha preparada;
- Campanha publicada.

Publicação histórica antiga não encerra a campanha atual.
Só conta:
- registro ligado à campanha preparada atual; ou
- publicação manual feita dentro da janela atual da campanha.

Campanhas preparadas recebem botão `Registrar publicação`.
Campanhas publicadas mostram canal/data e podem registrar outro canal.

## Diversidade social
A memória social aplica um ajuste pequeno na escolha do produto do Plano Executivo:
- publicado há até 7 dias: -18;
- até 14 dias: -12;
- até 30 dias: -6;
- sem publicação registrada ou há 45+ dias: pequeno bônus.

Esse ajuste serve somente para diversidade de divulgação.
Não é previsão de vendas e não substitui prontidão do produto/campanha.

## Imagens sociais
Imagem social não vira foto principal do Catálogo.
Depois de registrada, pode ser aproveitada com confirmação como:
- referência secundária;
- variação do produto.

A origem fica registrada em `BancoImagensHistorico`.

## Integração futura Meta
A estrutura `publicacoes_sociais` foi criada para receber futuramente dados da API oficial da Meta sem precisar refazer o histórico.

## Segurança
- não publica automaticamente;
- não presume que post ou réplica aconteceu;
- não faz scraping contínuo;
- links inválidos são bloqueados;
- foto social não substitui foto principal;
- nada é vinculado ao Catálogo sem confirmação do usuário.
