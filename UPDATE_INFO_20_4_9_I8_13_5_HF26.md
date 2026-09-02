# 20.4.9-I8.13.5-HF26 — THU • Plano de amanhã

Base funcional: **HF25 homologada**.

## Objetivo
Transformar a prevenção qualitativa da HF25 em uma preparação curta para o próximo dia, sem inventar capacidade produtiva e sem adiar urgências que já precisam ser resolvidas hoje.

## Mudanças
- Novo serviço somente leitura `thu_plano_amanha_service.py`.
- Novo expander dentro da própria `THU • Agenda executiva`: `🗓️ Plano de amanhã — DD/MM`.
- O plano reaproveita os sinais preventivos já homologados da HF25 e os organiza em:
  - `🏭 Produção`;
  - `📦 Materiais`;
  - `🚚 Saídas`.
- Pedidos já **Prontos** com retirada/entrega prevista para amanhã entram como preparação de saída.
- Atrasos e pedidos ainda **não Prontos** com entrega amanhã **não entram no Plano de Amanhã**, pois continuam como urgência atual em `Fazer agora`.
- Deduplicação por proposta: o mesmo pedido aparece no máximo uma vez no plano.
- Nenhuma ação do plano grava status, contato, produção, material ou entrega.

## Segurança e compatibilidade
- Nenhum banco/JSON/SQL novo.
- Importação resiliente: se o módulo da HF26 ainda não tiver subido, a Central continua funcionando com HF25.
- O radar preventivo da HF25 permanece a fonte de prevenção; a HF26 apenas o organiza para o próximo dia.
- `VERSAO` e `VERSAO.txt` alinhados em **20.4.9-I8.13.5-HF26**.
