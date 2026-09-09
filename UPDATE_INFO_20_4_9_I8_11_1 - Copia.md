# 20.4.9-I8.11.1 — Central de Faturamento Mensal

Base: 20.4.9-I8.11-HF2 homologada.

## Escopo
- Nova Central de Faturamento Mensal no perfil Jorge (rollout primeiro no Jorge).
- Agrupa propostas mensais por cliente e ciclo/competência conforme o dia de fechamento do Perfil Comercial.
- Somente propostas aprovadas e entregues entram no valor elegível para fechamento.
- Fluxo financeiro: Em aberto → Fechado → Faturado → Recebido.
- Ao registrar o recebimento do fechamento, as propostas vinculadas são marcadas como pagas automaticamente; não é necessário abrir cada proposta.
- Fechamentos armazenam apenas referências das propostas e total financeiro negociado, sem duplicar preços de produto, fotos, descrições ou o Catálogo Oficial.
- Reabertura é permitida somente antes de marcar como Faturado.
- Novas propostas que surjam após um fechamento podem formar complemento sem alterar o fechamento já registrado.
- Novo banco `faturamento_mensal_db.json` incluído no backup completo e na verificação de integridade.

## Regra de ciclo
Exemplo: cliente fecha dia 1 e vence dia 30. Uma entrega em 18/08 pertence à competência Setembro/2026, com fechamento previsto em 01/09 e vencimento em 30/09.

## Segurança
- Anna não recebe esta nova Central nesta versão. A extensão depende de homologação no perfil Jorge.
- O Catálogo Oficial continua sendo a única fonte de preço de produto.
