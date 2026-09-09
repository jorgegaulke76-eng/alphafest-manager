# 20.4.9-I5 — THU Plano Executivo de Campanhas

Base: Atual 2049I4 aprovada.

## Objetivo
Fechar o elo entre oportunidade de campanha e execução do trabalho.
O THU não apenas identifica a campanha: ele mostra a próxima ação necessária e o prazo de preparação.

## Plano Executivo
Novo painel:
`🧭 Assistente THU • Plano Executivo de Campanhas`

Para cada oportunidade do Calendário, o THU cruza:
- antecedência e data da campanha;
- elegibilidade confirmada no Catálogo;
- completude do cadastro;
- existência de arte na Biblioteca;
- prioridade de divulgação;
- campanhas sugeridas já salvas pelo THU.

## Etapas automáticas do plano
- Revisar elegibilidade;
- Revisar cadastro;
- Cadastrar arte;
- Preparar campanha;
- Campanha preparada.

A etapa é calculada a partir do estado real do sistema. Nenhuma etapa altera o Catálogo ou aprova uma campanha sozinha.

## Prazos
O prazo `Preparar até` usa a antecedência cadastrada no Calendário.
O plano diferencia:
- Ação imediata;
- Preparação atrasada;
- Preparar hoje;
- Preparar em X dias;
- Próxima;
- Programada;
- Preparada.

## Ações integradas
### Revisar elegibilidade
Abre a revisão assistida I4.

### Revisar cadastro
Abre o produto oficial para completar os dados.

### Cadastrar arte
O THU retorna ao formulário `Adicionar arte pronta para postagem` e já preenche:
- produto;
- categoria;
- campanha/tema.

A foto continua dependendo de upload manual.

### Preparar campanha
Abre o compositor THU com:
- produto oficial;
- campanha;
- arte recomendada.

### Campanha preparada
O plano reconhece a copy já salva em `thu_campanhas_sugeridas` e permite visualizar Feed e Story/Status.

## Central do Dia
Novo resumo compacto:
`🧭 THU • Próximas ações de Marketing`

Mostra as 4 prioridades de Marketing mais importantes dentro da Central.

## Segurança
- não publica automaticamente;
- não aprova campanha;
- não habilita produto em campanha;
- não cria arte;
- não altera preço/material/descrição;
- apenas organiza e encaminha cada pendência para o fluxo oficial correspondente.
