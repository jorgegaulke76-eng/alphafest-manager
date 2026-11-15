# HF65.24.11 — Atendimento Inteligente AlphaFest

Base: HF65.24.10 (favicon oficial e demais correções anteriores).

## Recursos
- No site público, guarda durante esta sessão (até 45 minutos de inatividade) os produtos, categorias e artigos acessados por interações do usuário.
- No clique em um link de atendimento `wa.me` ou `api.whatsapp.com/send`, acrescenta à **mensagem preenchida pelo WhatsApp** uma seleção dos interesses consultados (até 4 produtos, 2 categorias e 2 dicas).
- Não usa nome, telefone, endereço IP, parâmetros de URL nem dados pessoais para montar o resumo.
- Não cria identificação individual adicional, não grava a sequência no banco e não envia mensagens automaticamente.
- O cliente pode editar ou apagar o texto antes de confirmar o envio no WhatsApp.
- Para o histórico de navegação, a lista fica apenas em `sessionStorage`, isolada ao contexto da aba; ao fechar a aba ou após 45 min sem atividade registrada, a lista deixa de valer.
- O script é incluído no HTML do site e nas páginas de dicas **somente no pacote publicado**, sem alterar a prévia ou dados operacionais.

## Homologação
1. Publicar pelo fluxo homologado do Manager somente após conferir a prévia.
2. No site aberto, acessar um produto e uma dica, depois clicar no WhatsApp.
3. Verificar se a mensagem pré-preenchida contém esses interesses e pode ser editada.
4. Confirmar no WhatsApp se a mensagem foi enviada. O Manager **não dispara** a mensagem.

## Nota de transparência
O cliente deve ser informado no site, na política/aviso de privacidade, que itens consultados durante a visita podem ser incluídos na mensagem de contato. Essa alteração não substitui uma avaliação de conformidade com a LGPD.
