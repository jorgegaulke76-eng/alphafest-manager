# 20.4.9-I8.11-HF1 — Hotfix Jorge: Novo Orçamento + Identificação por WhatsApp

## Escopo
Hotfix restrito ao perfil Jorge. A Anna permanece no fluxo homologado anterior até validação explícita desta correção.

## Correções
- Corrige a navegação programática para **Novo Orçamento** em todas as telas do Jorge.
- Impede que o valor persistido do seletor da área Operação sobrescreva o destino solicitado por botões/atalhos.
- Botões **Novo orçamento** em Relacionamentos e Pesquisa Global agora carregam o cliente e abrem o formulário diretamente.
- No Novo Orçamento do Jorge, o WhatsApp identifica automaticamente um relacionamento cadastrado.
- Ao reconhecer o WhatsApp, preenche Nome/Razão Social e CPF/CNPJ a partir do cadastro mestre.
- Exibe imediatamente resumo do Perfil Comercial: mensalista, fechamento/vencimento e quantidade de preços especiais.
- Mantém a aplicação I8.11: preço oficial atual − abatimento fixo em R$ = preço final da proposta.

## Segurança de rollout
- Nenhuma alteração foi aplicada ao modal operacional da Anna nesta versão.
- Nenhum JSON comercial é migrado ou modificado pelo pacote.
- I8.11.1 permanece reservada para a futura Central de Faturamento Mensal.
