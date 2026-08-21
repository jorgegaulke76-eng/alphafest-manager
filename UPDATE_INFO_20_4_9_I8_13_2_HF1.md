# 20.4.9-I8.13.2-HF1 — Reconhecimento seguro de aliases na Reserva

## Correção
A Central de Reserva passa a reconhecer corretamente produtos da proposta quando o nome está cadastrado como alias do Catálogo Oficial, inclusive em cadastros legados onde vários aliases ficaram armazenados dentro de uma única entrada separados por vírgulas, ponto e vírgula, barra vertical, bullet ou quebra de linha.

## Ordem de resolução
1. Nome oficial exato/normalizado.
2. Alias exato/normalizado, somente se pertencer a um único produto oficial.
3. Saneamento forte e único já existente.
4. Em zero correspondências ou ambiguidade, a reserva continua bloqueada.

## Segurança
- Nenhum alias é criado ou gravado automaticamente.
- O Catálogo Oficial não é alterado por esta atualização.
- Se o mesmo alias apontar para mais de um produto, o vínculo automático é recusado.
- Depois do vínculo, a Ficha Técnica continua sendo obrigatória para liberar a reserva.
- Nenhum banco novo e nenhuma alteração nos JSONs operacionais da base.

## Interface
Quando o vínculo ocorre por alias, a prévia mostra explicitamente:
`✅ Vinculado pelo alias: item da proposta → produto oficial`.
