# 20.4.9-I8.13.4-HF7 — Saneamento Seguro de Status Históricos

- Prévia explícita das inconsistências históricas que podem ser corrigidas sem inferência comercial.
- Regras automáticas permitidas: Entregue implica Pronto; Pronto implica Aprovado; Pago implica Aprovado.
- Nunca infere Pago, nunca desfaz status, não altera estoque e não cria datas retroativas.
- Cada proposta é atualizada sobre leitura fresca/CAS e cada correção confirmada é registrada na Auditoria Oficial.
- Depois do saneamento, Fluxo/Produção/Risco/Entregas são reconciliados novamente pela Fonte Única.
- Auditoria de sincronização também detecta Pronto sem Aprovado.
