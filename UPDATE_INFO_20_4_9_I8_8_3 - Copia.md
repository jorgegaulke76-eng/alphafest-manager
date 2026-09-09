# 20.4.9-I8.8.3 — Modelos de Catálogo AlphaFest

Base exclusiva: 20.4.9-I8.8.2 homologada.

## Objetivo
Transformar configurações recorrentes do Gerador em modelos reutilizáveis, sem criar uma segunda fonte de produtos ou dados comerciais.

## Entrega
- Nova aba `🧩 Modelos I8.8.3`.
- Três modelos fixos do sistema:
  - `Catálogo Completo`;
  - `Catálogo sem preços`;
  - `Catálogo Corporativo` (sem preços e somente com produtos que tenham foto oficial).
- Modelos automáticos por categoria oficial.
- Modelos automáticos por campanha oficial existente.
- Os modelos automáticos são recalculados pelo Catálogo Oficial e surgem/desaparecem conforme categorias e campanhas atuais.
- Seletor de modelo integrado ao `Gerador I8.7.1`.
- Ao aplicar um modelo, a seleção de produtos é recalculada a partir dos filtros atuais; nenhum produto fica gravado dentro do modelo.
- Possibilidade de salvar a configuração atual do Gerador como `Meu modelo`.
- Modelo personalizado pode usar categorias específicas ou `todas as categorias atuais e futuras`.
- Modelo personalizado pode ser atualizado após ser aplicado no Gerador.
- Gestão de modelos personalizados com duplicação, arquivamento/reativação e Lixeira com restauração/exclusão definitiva.
- Modelos personalizados incluídos no backup completo e na verificação de integridade.
- Auditoria das operações de salvar, atualizar, duplicar, arquivar, reativar, excluir e restaurar.

## Regra arquitetural preservada
Um modelo guarda somente configuração de apresentação e filtros: título, subtítulo, rodapé, campanha, categorias e opções de exibição. Ele **não guarda produtos, preço, foto, descrição, material ou snapshot comercial**.

Ao aplicar qualquer modelo, os produtos elegíveis são definidos novamente pelo Catálogo Oficial atual.

## Proteções
- Modelo personalizado com campanha que não existe mais é bloqueado até ser corrigido, evitando ampliar silenciosamente a seleção.
- Modelo com categorias removidas do Catálogo Oficial é sinalizado.
- Categorias equivalentes continuam usando a blindagem da I8.7.1.
- A Prévia Interna I8.8.2 continua usando o mesmo HTML da exportação.

## Sem regressão
Cadastro, Produtos, Saneamento, Acervo histórico, Gerador I8.7.1, Prévia I8.8.2, Central, Lixeira da Central e Catálogo para cliente permanecem preservados.
