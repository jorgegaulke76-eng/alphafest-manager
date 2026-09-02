# 20.4.9-I8.13.5-HF21 — THU • Sem avanço registrado

Base funcional: **HF20 homologada**.

## Objetivo
Usar as fotografias diárias já registradas pela Agenda da Anna para ajudar o Jorge a identificar pedidos que permanecem no mesmo estágio/status sem esperar que o problema fique invisível até o prazo final.

## Novo bloco — Jorge
- Adiciona **⏳ THU • Sem avanço registrado** na Central do Jorge.
- O bloco é somente leitura e compara a Agenda atual com as fotografias diárias da Anna.
- Um sinal pode aparecer imediatamente quando um pedido com entrega hoje/vencida continua no mesmo estágio desde a abertura do dia.
- Com o acúmulo das fotografias, o THU também identifica propostas que permanecem na mesma fase por **2 ou mais dias**.
- Prefixos temporais como `ATRASADO`, `Entrega hoje` e `SAÍDA ATRASADA` não são tratados como mudança de estágio por si só.
- O THU diferencia os próximos passos conforme a fase: aprovação, pagamento, produção ou retirada/entrega.

## Regra de segurança
- **Sem avanço** significa apenas **sem mudança de status registrada no AlphaFest Manager**.
- O sistema não afirma que não houve trabalho físico/offline.
- Nenhuma mensagem é enviada.
- Nenhum contato é registrado.
- Nenhuma aprovação, pagamento, produção, Pronto ou Entregue é alterado pelo radar.
- A interface possui apenas orientação e **Abrir pedido**.

## Compatibilidade
- Usa o documento `agenda_anna_snapshots_db` já criado no ciclo HF19/HF20; não cria banco/tabela novo.
- Importação resiliente: se o novo serviço não carregar, o restante do Manager continua abrindo normalmente.
