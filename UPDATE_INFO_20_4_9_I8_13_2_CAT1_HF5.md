# AlphaFest Manager 20.4.9-I8.13.2-CAT1-HF5

## Orçamento — preenchimento pelo Catálogo Oficial
- A seleção de produto continua híbrida: Catálogo Oficial pesquisável por nome/alias + produto livre.
- Ao selecionar um produto oficial, o item recebe automaticamente o preço cadastrado, material/composição e descrição curta.
- Os dados continuam editáveis somente naquela proposta; o cadastro oficial não é alterado.
- O item preserva referência ao CatalogoId e snapshots de categoria, material e descrição.
- No Jorge, a seleção do produto foi retirada de dentro do `st.form` para que o preenchimento aconteça imediatamente após a escolha.
- O Perfil Comercial continua sendo aplicado sobre o preço oficial carregado.

## Catálogo — galeria estilo marketplace
- Até 5 mídias por produto.
- A primeira foto é a principal/capa.
- Pode usar 5 fotos, ou até 4 fotos + 1 vídeo.
- Vídeo é complementar e não substitui a foto principal.
- Permite fotos locais, URLs e Google Drive; vídeo por link ou upload MP4/MOV/WebM.
- Ao editar, é possível escolher qual foto existente será a principal.
- Catálogo HTML mostra foto principal + miniaturas e atalho para vídeo.
- PDF passa a aproveitar várias fotos; vídeo público recebe QR para acesso.

## Segurança
- Nenhum JSON operacional é migrado ou reescrito pela atualização.
- Produtos livres continuam permitidos no orçamento.
- Produtos legados com mais de 5 mídias continuam legíveis; ao editar/salvar, o Manager exige adequação ao novo limite.
