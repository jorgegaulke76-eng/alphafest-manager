# 20.4.9-I4 — THU Revisão de Elegibilidade de Campanhas

Base: 20.4.9-I3.2.1 aprovada.

## Objetivo
Transformar a relação produto × campanha em uma revisão assistida, sem autorizações automáticas.

## Fontes usadas como evidência
- Calendário Comercial: campo `produtos` da campanha;
- Catálogo: nome oficial, aliases, categoria e subcategoria;
- Biblioteca: arte já relacionada ao produto e à campanha;
- Acervo histórico do site: links úteis encontrados dentro da página histórica da campanha.

## Fluxo
O THU separa:
- produtos já elegíveis;
- produtos sugeridos para revisão;
- sugestões do Calendário sem correspondência segura no Catálogo.

Cada candidato recebe:
- índice de evidência de 0 a 100;
- explicação de onde veio a sugestão;
- foto do Catálogo, quando houver;
- campanhas já permitidas;
- pendências reais do cadastro.

`Campanhas/Datas` não aparece como pendência nessa tela porque é justamente o campo que está sendo revisado.

## Confirmação
Os checkboxes começam desmarcados.
Somente os produtos selecionados e confirmados entram em `CampanhasPermitidas`.

A confirmação registra em `HistoricoElegibilidadeTHU`:
- campanha;
- ação;
- evidências;
- fontes;
- data/hora;
- usuário.

## Acessos
- Central Operacional da Anna > Catálogo > `Revisar campanhas`;
- Central do Dia, quando uma campanha não possui produtos habilitados;
- Marketing > THU Prioridade de Divulgação;
- Marketing também permite revisar outros produtos mesmo quando já existem elegíveis.

## Segurança
- nenhuma campanha é adicionada automaticamente;
- produto Permanente continua elegível sem duplicar campanha;
- campanha fora das opções oficiais do Catálogo não pode ser gravada;
- sugestões sem correspondência segura são apenas informadas;
- o acervo histórico do site é evidência auxiliar, nunca fonte oficial.
