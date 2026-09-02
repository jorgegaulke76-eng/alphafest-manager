# 20.4.9-I8.13.5-HF27 — THU • Memória de tempo de ciclo observado

Base funcional: **HF26 homologada**.

## Objetivo
Criar a base factual necessária para uma futura leitura quantitativa de capacidade sem inventar tempo de mão de obra ou velocidade produtiva.

## O que passa a ser observado
- Uma transição explícita de item para `Em produção` abre um ciclo observado.
- A conclusão explícita em `Pronto` ou `Entregue` fecha a amostra.
- O intervalo é chamado de **tempo de ciclo observado**, pois pode incluir pausas, espera e tempo de máquina autônoma.
- Pular diretamente para `Pronto` sem início confiável não gera amostra inventada.
- Registros anteriores à HF27 só são recuperados quando a timeline contém início explícito de produção e conclusão compatível.
- A quantidade do item é preservada em cada amostra para evitar comparar lotes diferentes como se fossem equivalentes.

## Jorge • Central do Dia
Novo expander dentro da Agenda Executiva:
- `⏱️ Memória de tempos de produção · HF27`;
- total de ciclos observados;
- produtos com amostras;
- ciclos em andamento com início confiável;
- itens em produção sem início confiável;
- tabela por produto com número de amostras, mediana do ciclo, faixa observada, quantidade observada e processos associados.

## Regras de segurança
- A HF27 **não calcula capacidade exata**.
- A HF27 **não altera prazo prometido**.
- A HF27 **não mede mão de obra**.
- Nenhuma transição de produção é criada automaticamente apenas para gerar amostra.
- Amostras são metadados do próprio `producao_db`; não há banco/JSON/SQL novo.
- Importação resiliente preserva a Central caso o módulo da HF27 ainda não tenha subido em uma atualização parcial.

## Próxima evolução somente após uso real
Acumular amostras e observar variação por produto/quantidade. Só então avaliar modelos quantitativos de capacidade, com critérios mínimos de amostragem e sem confundir tempo de ciclo com tempo produtivo ativo.
