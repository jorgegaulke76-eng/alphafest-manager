# HF65.24.38 — Operação sob encomenda e fila de pedidos

## Motivo
Na AlphaFest, o produto final é personalizado, produzido sob encomenda. A dependência de reserva e consumo de estoque não deve impedir pedidos aprovados de seguir para Pronto e Entregue.

## Mudanças
- Status oficiais preservados: Pedido/Orçamento, Aprovado, Pronto e Entregue. Pago permanece como controle financeiro separado; Cancelado continua disponível como encerramento.
- Não exige reserva, liberação ou baixa automática de material para iniciar produção, marcar Pronto ou Entregue.
- A fila de produção usa aprovação, etapa manual e prazo de entrega; atraso considera o prazo, não saldo de estoque.
- Central deixa de apresentar as antigas pendências de material e apresenta a situação de encomendas.
- Retirada do módulo de Estoque/Compras da navegação principal (arquivos e histórico conservados; nenhuma exclusão de registros).
- Produtos dos orçamentos sem vínculo seguro ao Catálogo continuam sinalizados; nova visão na Central oferece cadastro assistido, sem duplicar produtos existentes.
- Nenhum pedido represado é concluído automaticamente. A equipe deve atualizar os status conforme a produção real.

## Instalação
Substituir arquivos da pasta do repositório pela pasta do ZIP; GitHub Desktop: Commit + Push origin; reiniciar/recarregar Streamlit e verificar a versão na tela.

## Validação sugerida
- Pedido aprovado anteriormente impedido por material: agora deve permitir atualização para Pronto, mantendo histórico.
- Pedido Pronto: pode ser marcado Entregue e sair da fila operacional.
- Pedido sem aprovação: não deve iniciar produção como se estivesse aprovado.
- Produto livre ausente no catálogo: aviso de cadastro e botão na Central/Orçamento.
- Financeiro e pedidos antigos: os históricos devem permanecer intactos.

## Importante
Esta versão altera o Manager, não a publicação do site. A ocultação de controles de estoque NÃO apaga informações financeiras, movimentações, documentos ou registros de pedidos. Os dados antigos permanecem para auditoria.
