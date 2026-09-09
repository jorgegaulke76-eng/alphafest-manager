# 20.4.9-I8.13.2-CAT1-HF12

## Correção do texto público da proposta
- Cabeçalho da proposta não duplica mais a cidade quando `nome_maiusculo` já contém `ITATIBA`.
- A linha pública `Empresa` no bloco PIX remove CPF/CNPJ eventualmente anexado ao nome do favorecido.
- A configuração interna e os dados fiscais permanecem intactos; a sanitização ocorre somente na apresentação/geração da proposta.
- Base: HF11 homologada enviada pelo usuário.
