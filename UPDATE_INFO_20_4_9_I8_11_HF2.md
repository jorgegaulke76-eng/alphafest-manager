# 20.4.9-I8.11-HF2 — Extensão do Perfil Comercial para Anna

## Escopo
Extensão para o perfil Anna somente após homologação completa do HF1 no perfil Jorge. A lógica comercial do Jorge permanece como referência oficial e não foi substituída.

## Entregas
- WhatsApp no modal de orçamento da Anna identifica automaticamente relacionamento já cadastrado.
- Ao reconhecer o cliente, preenche Nome/Razão Social e CPF/CNPJ a partir do cadastro mestre.
- Exibe o Perfil Comercial antes da inclusão de itens: mensalista, fechamento, vencimento e quantidade de abatimentos ativos.
- Itens da Anna passam a usar a mesma função homologada no Jorge para preços especiais: preço oficial atual − abatimento fixo em R$ = preço final da proposta.
- Propostas mensalistas criadas pela Anna recebem modalidade de cobrança, relacionamento e status financeiro compatíveis com o Perfil Comercial.
- Itens com preço especial registram base oficial, abatimento fixo e preço final aplicado naquele momento, preservando o histórico da proposta.
- Botão para recalcular itens existentes pelo Perfil Comercial quando necessário.
- Desconto adicional da proposta continua separado dos abatimentos fixos por produto.

## Proteções preservadas
- Nenhuma porcentagem é usada para descontos especiais.
- Catálogo Oficial não é alterado.
- Abatimento maior que o preço oficial continua bloqueado.
- Nenhum cadastro ou regra comercial é criado automaticamente pela proposta.
- Fluxo HF1 do Jorge permanece intacto.
