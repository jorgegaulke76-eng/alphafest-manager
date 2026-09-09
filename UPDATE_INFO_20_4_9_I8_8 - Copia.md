# 20.4.9-I8.8 — Central de Catálogos AlphaFest

Base exclusiva: 20.4.9-I8.7.1 (`Atual 2049I871.zip`).

## Objetivo
Transformar o Gerador de Catálogos homologado em um módulo operacional permanente, permitindo salvar, localizar, reutilizar e administrar configurações de catálogo sem criar uma segunda fonte de dados comerciais.

## Regra arquitetural principal
O **Catálogo Oficial continua sendo a única fonte de verdade** para produto, preço, foto, descrição, material, variações, status e campanhas.

A Central I8.8 **não salva snapshots comerciais dos produtos**. Cada catálogo salvo guarda apenas:
- identificação interna do catálogo;
- título, subtítulo e observação de rodapé;
- campanha/filtro usado na montagem;
- categorias selecionadas;
- opções de exibição;
- referências leves para reencontrar os produtos oficiais;
- datas, usuário e revisão da configuração.

Ao usar **Gerar novamente com dados atuais**, o HTML é reconstruído a partir do Catálogo Oficial naquele momento.

## Entregas da I8.8
- Nova aba `🗂️ Central I8.8` dentro do Catálogo.
- Botão `Salvar catálogo na Central I8.8` no Gerador I8.7.1.
- Nome interno separado do título público.
- Listagem de catálogos salvos com pesquisa e filtro por status.
- Indicadores de ativos, arquivados e referências pendentes.
- Ação `Abrir` para conferir quais produtos oficiais estão ligados à configuração.
- Ação `Editar` para alterar seleção, filtros e opções de exibição.
- Ação `Duplicar` para criar nova configuração sem alterar a original.
- Ação `Gerar novamente com dados atuais`.
- Ação `Arquivar` e `Reativar`.
- Exclusão protegida por confirmação e envio para a Lixeira.
- Restauração de `Catálogo gerado` pela Lixeira.
- Auditoria das operações principais da Central.
- `catalogos_gerados_db` incluído no backup completo e na verificação de integridade.

## Blindagem de referências
A resolução de produto prioriza:
1. `CodigoInterno`, quando existente e único;
2. identidade normalizada de nome + categoria;
3. índice histórico somente quando ainda confirma a mesma identidade;
4. nome único como último vínculo seguro.

Quando uma referência não pode ser resolvida com segurança, ela fica **pendente**. O sistema não substitui silenciosamente por outro produto nem usa uma cópia antiga.

## Comportamento quando o Catálogo Oficial muda
- preço alterado: próxima geração usa o novo preço;
- foto alterada: próxima geração usa a nova foto;
- descrição/material alterados: próxima geração usa os novos dados;
- produto inativado: não entra na saída atual e a Central informa a situação;
- campanha/elegibilidade alterada: a próxima geração respeita a elegibilidade oficial atual e retira produtos que deixaram de participar daquela campanha;
- produto removido/renomeado sem referência estável: vínculo fica pendente e pode ser corrigido na edição.

## Preservado
- Gerador I8.7.1 homologado.
- Saneamento.
- Acervo histórico.
- Cadastro e edição de produtos.
- Aba antiga `Catálogo para cliente` como fallback.
- Regras de preço atual e ausência de quantidade mínima.
- Nenhum preço histórico é importado para a Central.

## Validação técnica
- `py_compile` em todos os arquivos Python.
- Testes puros de criação, duplicação e resolução de referências.
- Teste de reordenação do Catálogo Oficial sem perda de vínculo seguro.
- Teste de produto removido: referência passa a pendente sem substituição silenciosa.
- Teste de elegibilidade de campanha: produto que deixa de participar da campanha salva não entra na nova geração.
- Verificação de que as referências salvas não carregam preço, foto, descrição ou material.
- Verificação de inclusão da Central no backup e restauração pela Lixeira.

## Próximo passo após homologação humana
I8.8.1 — Prévia interna do catálogo antes de gerar/baixar, mantendo a Central I8.8 como base operacional.
