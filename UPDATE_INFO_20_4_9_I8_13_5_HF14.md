# AlphaFest Manager 20.4.9-I8.13.5-HF14

## THU • Retornos Comerciais — fase inicial no Jorge

Base: **20.4.9-I8.13.5-HF13 homologada**.

### Objetivo

Iniciar o novo ciclo de estabilidade, automações e inteligência do THU sem alterar a Central da Anna e sem automatizar decisões comerciais. O foco desta hotfix é dar ao Jorge uma fila confiável de orçamentos que realmente foram enviados e ainda aguardam aprovação.

### Novo comportamento

- Após realmente enviar um orçamento, Jorge pode usar **Registrar envio**.
- O registro grava na própria proposta:
  - primeiro envio (`enviado_em`);
  - último contato (`ultimo_envio_em`);
  - usuário que registrou;
  - quantidade de contatos registrados.
- Um novo contato pode ser registrado depois de um follow-up, reiniciando o tempo de acompanhamento do THU.
- A Central do Jorge ganha **THU • Retornos comerciais** com:
  - orçamento e cliente;
  - tempo desde o último contato;
  - impacto da proximidade/atraso do prazo;
  - prioridade sugerida;
  - próxima ação;
  - botão para abrir o WhatsApp com uma mensagem de acompanhamento sugerida;
  - botão para registrar que o contato foi realizado;
  - botão para abrir a proposta.
- O Histórico do Jorge também permite registrar envio/novo contato.

### Segurança da automação

- Abrir o WhatsApp **não é tratado como prova de envio**.
- O THU só acompanha propostas cujo envio foi explicitamente registrado.
- Nenhuma mensagem é enviada automaticamente.
- Nenhuma proposta é aprovada, encerrada, paga, marcada como pronta ou entregue por esta função.
- A Fonte Única de Status continua soberana.
- Propostas aprovadas, entregues ou encerradas saem automaticamente da fila de retorno.
- A Central da Anna permanece sem esta nova interface durante a homologação.

### Arquitetura

Novo serviço puro `thu_comercial_service.py`, sem Streamlit/Supabase, responsável por:

- registrar metadados de envio/retorno;
- calcular a fila comercial;
- priorizar prazo vencido/próximo e tempo sem retorno;
- preparar mensagem sugerida sem disparo automático.

### Homologação sugerida

1. No perfil Jorge, criar ou abrir um orçamento ainda não aprovado.
2. Enviar normalmente pelo WhatsApp.
3. Clicar em **Registrar envio**.
4. Abrir a Central do Dia e confirmar que o orçamento aparece em **THU • Retornos comerciais**.
5. Confirmar que o botão **Retomar** apenas abre o WhatsApp com a mensagem sugerida.
6. Clicar em **Registrei contato** depois de um retorno e confirmar que o tempo de acompanhamento é reiniciado.
7. Aprovar a proposta e confirmar que ela deixa a fila de retornos comerciais.

### Testes

- **74 testes automáticos aprovados**.
- Novos testes cobrem registro de primeiro/último contato, exclusão de propostas aprovadas/encerradas, priorização por prazo, priorização por tempo sem retorno e preparação segura do WhatsApp.
