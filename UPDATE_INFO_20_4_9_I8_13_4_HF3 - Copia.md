# AlphaFest Manager 20.4.9-I8.13.4-HF3

## Integração definitiva Central do Dia ↔ Fluxo de Pedidos

Correção focada em garantir que o universo operacional mostrado na Central do Dia seja o mesmo universo representado no Fluxo.

### O que mudou

- O Histórico oficial passa a definir obrigatoriamente quais propostas ativas precisam existir no Fluxo.
- `producao_db` continua guardando somente a etapa manual, prioridade, processos e observações; ele não decide mais se um pedido existe no Fluxo.
- Se uma tarefa ainda não existir em `producao_db`, o Manager cria a projeção imediatamente e tenta persistir o espelho com compare-and-swap.
- Conflitos entre Jorge e Anna durante a reconciliação não fazem pedidos desaparecerem.
- Se a persistência do espelho falhar temporariamente, o pedido oficial continua visível no Fluxo e a reconciliação é tentada novamente.
- Propostas antigas sem itens estruturados recebem uma representação operacional defensiva para não sumirem do Fluxo.
- Propostas entregues/encerradas deixam a fila operacional, mas os registros antigos de produção permanecem preservados como inativos.
- O Fluxo mostra diagnóstico de cobertura `Central ↔ Fluxo`.
- Anna e Jorge passam a abrir a mesma tela operacional de Fluxo. O antigo diálogo paralelo da Anna deixa de ser o caminho principal.
- Rótulo `Prontos` foi esclarecido para `Prontos p/ entrega`.

### Persistência

Foi adicionado `cloud_db.mutate_document`, que executa leitura fresca + compare-and-swap para reconciliações de documento inteiro. Isso evita sobrescrever uma gravação concorrente com uma cópia antiga.

### Segurança e custo

- Nenhum SQL novo.
- Nenhum serviço novo.
- Nenhuma API paga.
- Custo adicional: R$ 0,00.

### Validação

- 32 arquivos Python analisados sem erro de sintaxe.
- Teste de projeção Central → Fluxo aprovado para pendente de aprovação, aprovado, pronto e registro legado.
- Etapa manual existente preservada durante a reconciliação.
- JSONs operacionais preservados sem alteração.
