# 20.4.9-I8.13.4-HF6 — Auditoria de Sincronização Operacional

Objetivo: impedir divergências silenciosas entre Histórico, Central, Fluxo/Produção, Risco e Entregas, mantendo o Histórico/Proposta como Fonte Única Oficial.

## Mudanças

- Novo motor puro `consistencia_operacional_engine.py` para comparar as projeções operacionais com a Fonte Única.
- Auditoria identifica:
  - pedido operacional ativo sem representação no Fluxo;
  - tarefa ativa para pedido encerrado/entregue;
  - tarefa órfã;
  - pedido aprovado/aberto ausente ou indevido na previsão;
  - risco indevido para pedido encerrado, Pronto ou Entregue;
  - pedido Pronto ausente/indevido na fila de Entregas;
  - combinações de status que merecem revisão.
- Reparos automáticos são limitados ao espelho `producao_db`; nenhum status oficial é alterado pela auditoria.
- Gestão > Configurações > Núcleo Profissional > Auditoria ganha o botão **Auditar e sincronizar telas agora**.
- Central do Jorge exibe diagnóstico da coerência das telas.
- Fluxo exibe automaticamente a auditoria quando houver divergência.
- Compras/Estoque > Previsão de Produção usa leitura fresca do Histórico e mostra estado da sincronização.
- Health Monitor pode exibir `Telas operacionais: sincronizadas` após uma auditoria executada.
- Correção da I8.12.7: propostas encerradas/não fechadas não podem mais reaparecer como `Risco de atraso` só por manterem `Aprovado` legado.
- Correção da Central de Entregas: propostas encerradas não podem reaparecer na fila de saída por marcador legado de `Pronto`.

## Regra arquitetural

**Histórico/Proposta oficial = verdade principal.**

Fluxo/Produção guarda somente etapa manual; Risco, Entregas e painéis são projeções recalculadas. A auditoria não cria status paralelo.

## Custo

R$ 0,00. Não há serviço, API ou assinatura adicional.
