# 20.4.9-I8.13.5-HF34 — Health Monitor compatível com carga sob demanda

## Correção
- Corrige o falso alerta vermelho do Health Monitor introduzido pela otimização conservadora da HF33.
- O estado `sob demanda` passa a ser reconhecido como saudável: significa que o módulo ainda não precisou ser carregado, não que houve falha.
- O painel informa quantos módulos estão aguardando uso em carga sob demanda.
- Alpha Intelligence e Central de Oportunidades atualizam a mesma etapa do diagnóstico quando são abertas, evitando contagem duplicada.

## Preservação
- Mantém integralmente o carregamento preguiçoso e o ganho de performance da HF33.
- Nenhuma função homologada é removida, simplificada ou substituída.
- Fonte Única, sincronização Jorge/Anna, TTL de documentos, invalidação após gravação e arquivos operacionais permanecem inalterados.

## Homologação sugerida
1. Abrir Jorge > Central do Dia.
2. Confirmar `Sistema: Estável` em verde e Banco Online.
3. Confirmar mensagem de carga sob demanda normal enquanto os módulos opcionais não foram abertos.
4. Abrir Alpha Intelligence e Central de Oportunidades posteriormente para confirmar que seguem funcionando.
