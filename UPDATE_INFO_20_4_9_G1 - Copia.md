# 20.4.9-G1 — Períodos e Consistência dos Relatórios

Base: Atual 2049G.

## Correções principais
- novo filtro de período: Hoje, Este mês, Últimos 30 dias, Todo histórico e Personalizado;
- o mesmo período controla cards, gráficos, clientes e produtos;
- o período é baseado explicitamente na data de criação da proposta;
- o topo mostra o intervalo exato considerado;
- registros sem data válida são sinalizados e não entram silenciosamente em filtros por data;
- o gráfico de Orçamentos por período mantém datas como datetime e ordena cronologicamente;
- no modo Este mês, a quantidade de propostas mostra a conferência com o Painel Executivo;
- auditoria de resultados passa a auditar o período selecionado;
- nova auditoria de nomes de produtos possivelmente duplicados;
- a auditoria de nomes apenas sinaliza possíveis variações como “PAPEL ARROZ” e “PAPEL DE ARROZ”; não une nem renomeia automaticamente.

## Regra de segurança
Nenhum histórico, nome de produto ou valor é reescrito automaticamente.
