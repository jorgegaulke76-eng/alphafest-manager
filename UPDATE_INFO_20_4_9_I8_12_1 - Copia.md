# 20.4.9-I8.12.1 — Histórico de Compras por Fornecedor

Base exclusiva: 20.4.9-I8.11.3-HF2 homologada em 19/08/2026.

## Objetivo
Abrir o ciclo de inteligência de compras/custos sem transformar custo em preço de venda automático.

## Entregas
- Novo módulo `🧾 Compras & Custos` dentro da área Gestão, inicialmente somente no perfil Jorge.
- Fornecedor selecionado exclusivamente do Cadastro Mestre de Relacionamentos com papel `Fornecedor`.
- Registro de data da compra, produto/material, quantidade, unidade, custo unitário, total automático, NF/pedido/referência e observação.
- Vínculo opcional com produtos do Catálogo Oficial apenas como referência de gestão; o catálogo não é alterado.
- Comparação automática com a compra anterior do mesmo item, mesmo fornecedor e mesma unidade de medida.
- Alerta em R$ quando o custo unitário sobe ou cai.
- Resumo do mês: compras registradas, total comprado, fornecedores usados e compras com aumento de custo.
- Histórico pesquisável e filtrável por fornecedor e período.
- Lançamentos incorretos podem ser enviados à Lixeira pelo Jorge e restaurados pela Administração.
- `compras_db` incluído no backup geral.

## Regra comercial protegida
- Aumento de custo nunca altera automaticamente o preço de venda do Catálogo Oficial.
- O Manager apenas recomenda revisão humana dos produtos relacionados.
- Preços históricos/legados continuam sem virar preço oficial automaticamente.

## Compatibilidade e segurança
- Nenhuma regra de proposta, faturamento mensal, status, THU, Alpha Core, Radar, Catálogo ou Perfil Comercial foi modificada.
- A Central Operacional da Anna não recebe o módulo nesta etapa.
