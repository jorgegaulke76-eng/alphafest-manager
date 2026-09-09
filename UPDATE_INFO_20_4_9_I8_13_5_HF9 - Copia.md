# 20.4.9-I8.13.5-HF9 — Cliente por WhatsApp no Orçamento

Base: **20.4.9-I8.13.5-HF8**.

## Objetivo
Ao digitar o WhatsApp no Novo Orçamento, reconhecer automaticamente um cliente já cadastrado e carregar sua identificação, sem bloquear o fluxo de cliente novo.

## Comportamento
- WhatsApp já cadastrado: Nome/Razão Social e CPF/CNPJ são preenchidos automaticamente a partir de Relacionamentos.
- O seletor visual de cliente é sincronizado com o cadastro reconhecido.
- O WhatsApp digitado pelo operador é preservado exatamente como foi informado.
- WhatsApp não cadastrado: o orçamento permanece em **Cliente novo / digitar manualmente**, permitindo continuar o preenchimento normalmente no próprio orçamento.
- Ao trocar um WhatsApp reconhecido por um número novo, Nome/Documento que tinham sido preenchidos automaticamente são limpos para impedir mistura entre clientes.
- Se Nome/Documento tiverem sido alterados manualmente depois do autopreenchimento, a edição manual é preservada.
- A mesma regra foi mantida nos fluxos de Jorge e Anna.

## Preservado
- Orçamento + Catálogo da HF8;
- preço oficial e Perfil Comercial;
- Tema, Nome personalizado, Cor/Material, Idade/Data e Outros Detalhes continuam manuais;
- status Aprovado/Pago/Pronto/Entregue;
- histórico e vínculos existentes;
- nenhum cliente existente é alterado automaticamente.

## Homologação sugerida
1. Abrir Novo Orçamento.
2. Manter `Cliente novo / digitar manualmente` e digitar o WhatsApp de um cliente já cadastrado.
3. Confirmar que Nome e CPF/CNPJ aparecem automaticamente e o seletor passa a mostrar o cliente.
4. Trocar o WhatsApp para um número ainda não cadastrado.
5. Confirmar que o seletor volta para Cliente novo, os dados automáticos antigos não permanecem e é possível digitar o novo cliente normalmente.
6. Repetir com um WhatsApp contendo máscara/código 55 para validar a normalização.
