# AlphaFest Manager — HF30

## Catálogo: diagnóstico operacional otimizado

Primeiro passo em bloco operacional maior, mantendo o Catálogo Oficial em modo conservador.

- detecção de possíveis duplicidades movida para `catalogo_diagnostics_service.py`;
- cruzamento deixa de comparar indiscriminadamente todos os produtos e passa a usar índices por nome normalizado, alias e nome flexível;
- resultado é cacheado somente pelos campos que afetam o diagnóstico (Nome, Aliases e RevisõesSaneamentoTHU);
- qualquer alteração nesses campos invalida o cache automaticamente;
- decisões humanas de “não são duplicados” continuam sendo respeitadas;
- nenhuma união, exclusão, edição de preço, foto, publicação ou cadastro é automática;
- HF7, Template Anna e Marketing Engine permanecem congelados.
