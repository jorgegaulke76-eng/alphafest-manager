# AlphaFest Manager 20.4.9-I8.13.2-CAT1-HF6

## Cliente pesquisável + autopreenchimento no Novo Orçamento

- Jorge e Anna agora possuem um seletor pesquisável de clientes cadastrados antes dos campos manuais.
- A busca funciona pelo texto exibido com nome, WhatsApp, CPF/CNPJ e cidade.
- Ao selecionar um cliente, Nome/Razão Social, CPF/CNPJ e WhatsApp são preenchidos automaticamente a partir do cadastro mestre.
- Perfil Comercial existente continua sendo reconhecido: faturamento mensal e abatimentos por produto permanecem aplicados pela mesma fonte oficial.
- O preenchimento automático ocorre apenas quando a seleção muda; alterações manuais feitas só naquela proposta não são reescritas em reruns.
- Continua existindo a opção `Cliente novo / digitar manualmente`, sem obrigar cadastro prévio.
- A proposta passa a preservar também uma fotografia auxiliar de e-mail e cidade quando o cliente cadastrado possuir esses dados, mantendo `relacionamento_id` como vínculo mestre.
- Nenhum cliente é criado, alterado ou mesclado automaticamente pelo seletor.
