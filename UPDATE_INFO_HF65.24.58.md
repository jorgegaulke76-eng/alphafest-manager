# HF65.24.58 RC3 — Arte por versão e ficha de produção

**Pacote de homologação, não produção.** Baseado na HF65.24.57 e na prévia HF65.24.58 RC2.

## O que a operação terá após homologação
- Aprovação manual vinculada à arte ativa mais recente, com usuário e data do registro.
- Ao enviar, alterar, substituir ou arquivar uma arte, a confirmação anterior é reavaliada e, quando necessário, fica pendente.
- O checkbox é desmarcado quando a identidade da arte muda, mesmo que o ID permaneça igual. Após salvar, é necessário novo aceite para outro registro.
- O clique revalida a versão atual antes de gravar e usa a proteção CAS já adotada pelo Manager para projetos.
- A ficha de produção TXT inclui número da proposta, cliente, entrega, produtos, quantidades, especificações completas, observações internas e status da arte.

## O que não muda
- A aprovação comercial, o Fluxo e o banco de dados existente.
- O site público, o catálogo e a publicação.
- Nenhum pedido é alterado ao gerar a ficha.

## Atenções
- A aprovação é operacional, não prova automática do cliente.
- Alterações no conteúdo remoto de um arquivo sem troca de metadados não são detectáveis pela assinatura atual.
- A release definitiva depende do roteiro `VALIDACAO_HF65.24.58.md`.
