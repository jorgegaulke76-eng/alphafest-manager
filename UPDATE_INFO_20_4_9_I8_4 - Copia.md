# 20.4.9-I8.4 — Auditoria e Reparo de Fotos Quebradas

Base: 20.4.9-I8.3.

## Problema identificado
Alguns produtos exibiam `1 foto(s)`, porém a referência apontava para arquivo local
antigo/inexistente. A I8.3 considerava qualquer conteúdo no campo `Imagens` como foto
existente e, portanto, não tentava recuperar esse cadastro.

## Correção
Agora o Manager diferencia:
- foto realmente utilizável;
- referência comprovadamente quebrada;
- URL remota não verificada;
- produto realmente sem foto.

## Proteção
Uma foto válida nunca é removida.
Referências quebradas são preservadas em:
`ImagensInacessiveisHistoricoI84`

Somente depois disso elas deixam a galeria ativa.

## Ordem de recuperação
Quando o produto fica sem imagem válida:
1. BancoImagensHistorico;
2. VariacoesImagem;
3. ArquivosBiblioteca que sejam imagem/foto/referência;
4. Acervo Histórico de Catálogos, apenas página de produto único.

Páginas multiproduto continuam proibidas para recuperação automática.

## Auditoria profunda
No Acervo existe:
`🩺 Auditar e reparar fotos do Catálogo`

Essa ação também verifica URLs remotas. A verificação automática de sessão é mais leve
e não faz chamadas de rede em massa.

## Se não houver fonte recuperável
O sistema não inventa uma imagem.
A referência quebrada fica arquivada e o produto passa a aparecer corretamente como
sem foto, indicando necessidade de nova imagem.

## Campos não alterados
- preço;
- material;
- descrição;
- campanhas;
- aliases;
- quantidade mínima;
- vínculos de orçamento.
