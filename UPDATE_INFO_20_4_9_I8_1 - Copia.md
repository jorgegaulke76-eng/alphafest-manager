# 20.4.9-I8.1 — Fluxo de Cadastro Preparado

## Correção
`Preparar cadastro` agora abre imediatamente o formulário oficial do Catálogo.

Fluxo:
1. Acervo Histórico > Preparar cadastro;
2. PASSO 2/2 aparece na tela;
3. revisar campos;
4. informar/atualizar preço atual quando disponível;
5. clicar em `Salvar no Catálogo Oficial`;
6. somente então o produto é gravado.

## Recuperação
Páginas persistidas como `Em cadastro` mostram `Continuar cadastro`, permitindo
retomar o formulário mesmo depois de refresh/reinício do Streamlit.

## Segurança
- preparar não salva;
- preço histórico nunca vira preço atual;
- mínimo histórico nunca vira regra;
- só há gravação mediante clique explícito no botão de salvar.
