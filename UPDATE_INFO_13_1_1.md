# AlphaFest 13.1.1 — Estabilidade e navegação sob demanda

Base consolidada: `alphafest-manager-main80`.

## Perfil do Jorge

- Substituição da antiga fila horizontal de módulos por dois seletores compactos: **Área** e **Módulo**.
- Renderização sob demanda: apenas o módulo selecionado executa seu conteúdo.
- Interrupção imediata do ciclo anterior ao trocar de módulo, reduzindo processamento desnecessário.
- Cache de documentos mantido com TTL de 20 segundos para evitar consultas repetidas ao banco.
- Correção da prévia das Orientações do THU em Configurações.

## Perfil da Anna

- Central Operacional preservada integralmente.
- Nenhuma alteração de layout, posição de botões ou fluxo de trabalho.

## Testes

- Compilação sintática dos módulos Python principais.
- Verificação da versão no rodapé: `13.1.1`.
