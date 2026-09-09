# 20.4.9-I8.13.5-HF10 — Cliente novo cadastrado pelo próprio Orçamento

Base: **20.4.9-I8.13.5-HF9 homologada**.

## Objetivo
Completar o ciclo iniciado na HF9: além de reconhecer clientes existentes pelo WhatsApp, o Novo Orçamento passa a cadastrar no cadastro mestre o cliente realmente novo no momento de salvar a proposta.

## Comportamento
- WhatsApp/documento já cadastrado: reutiliza o cliente existente e mantém o Perfil Comercial atual.
- WhatsApp realmente novo: ao salvar o orçamento, cria um novo registro em Clientes/Relacionamentos e grava o `relacionamento_id` correto na proposta.
- O mesmo fluxo vale para Jorge e Anna.
- Repetir o salvamento depois de uma falha da proposta não duplica o cliente, porque o novo cadastro já passa a ser reconhecido pelo identificador.
- Ao editar uma proposta e trocar para um cliente novo, o vínculo antigo não é reaproveitado silenciosamente.
- Homônimos são protegidos: se um WhatsApp/documento novo foi informado, o sistema não liga o pedido a outro cadastro apenas porque o nome é igual.
- Cliente existente nunca é alterado automaticamente por esta hotfix.

## Integridade
- O cliente novo só é considerado cadastrado após confirmação da gravação do cadastro mestre.
- Se a gravação do novo cliente não for confirmada, a proposta não é salva com vínculo incompleto.
- Nenhum cliente histórico é migrado, mesclado ou regravado em lote.
- Orçamento + Catálogo da HF8 e reconhecimento por WhatsApp da HF9 permanecem preservados.

## Homologação sugerida
1. Abrir Novo Orçamento e informar um WhatsApp que não existe no cadastro.
2. Preencher o nome, adicionar um item e salvar a proposta.
3. Abrir Clientes/Relacionamentos e confirmar que o novo cliente foi criado.
4. Abrir a proposta e confirmar que ela está vinculada a esse cliente.
5. Fazer um segundo orçamento com o mesmo WhatsApp e confirmar que o cliente é reconhecido, sem duplicação.
6. Opcional: testar dois clientes com o mesmo nome e WhatsApps diferentes para confirmar que permanecem separados.

## Testes
- 64 testes automáticos aprovados.
- Incluídos testes de WhatsApp com código 55, proteção de homônimos, fallback por nome sem identificador e preparação segura do cadastro novo.
