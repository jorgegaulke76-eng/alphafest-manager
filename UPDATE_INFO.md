# AlphaFest Manager — HF62

## Clientes recorrentes e fechamento periódico

Atualização incremental sobre a HF61, preservando site, catálogo, produção, financeiro e regras já homologadas.

### Entregas
- identifica rapidamente na carteira de Relacionamentos os clientes com fechamento recorrente;
- periodicidade configurável por cliente: **Semanal**, **Quinzenal** ou **Mensal**;
- filtro da carteira por fechamento periódico e por periodicidade;
- marcador visual `[S]`, `[Q]` ou `[M]` na lista de relacionamentos;
- nova Central **Fechamentos Recorrentes**, reaproveitando o mesmo Financeiro e o mesmo histórico de pedidos;
- período sugerido automaticamente e datas ajustáveis antes de confirmar;
- somente pedidos **aprovados + entregues + ainda não fechados** entram no fechamento;
- um pedido já incluído em fechamento não reaparece em outro;
- boletim para conferência com **número do pedido, data do pedido, produto, tema, quantidade e valor**;
- a **data de entrega não aparece** no boletim;
- vários itens do mesmo pedido aparecem separadamente, mantendo o valor total do pedido apenas uma vez para a soma conferir;
- envio por WhatsApp, HTML e PDF;
- fluxo Fechado → Enviado/Faturado → Recebido preservado;
- ao registrar recebimento, os pedidos vinculados continuam sendo marcados como pagos automaticamente;
- reabertura auditada e correção de fechamento preservadas;
- clientes antigos de faturamento mensal são migrados por compatibilidade para periodicidade **Mensal**, sem migração de banco.

### Ciclos sugeridos
- Semanal: segunda a domingo;
- Quinzenal: dias 1–15 e 16–fim do mês;
- Mensal: mês calendário;
- o operador pode ajustar o início e o fim antes de fechar.

### Preservado
- HF61 — categorias rápidas por checkbox;
- HF60 — publicação Cloudflare;
- HF59 — Central do Site simplificada e multicategorias de produtos;
- HF58 — Galeria em múltiplas categorias;
- HF57 — categorias do site sem limite;
- HF56 — lightbox da Galeria pública;
- HF55 — exclusão individual de foto da Galeria interna;
- Template Mestre Comercial HF7 congelado;
- Template Anna homologado.
