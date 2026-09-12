# AlphaFest Manager — HF55

## Galeria: exclusão individual de foto

- adiciona a ação **Excluir foto** em cada trabalho ativo da Galeria;
- abre uma janela com todas as fotos do trabalho para escolher visualmente a imagem errada;
- exige confirmação individual antes da exclusão;
- preserva todas as demais fotos e metadados do trabalho;
- grava primeiro a nova lista no banco e somente depois remove o arquivo privado, evitando referência quebrada;
- ao excluir a última foto, remove automaticamente pré-seleção/destaque para impedir item vazio na futura Galeria do site;
- limpa o cache privado de imagens após a exclusão;
- registra a ação na auditoria quando disponível;
- HF7, Template Anna e Marketing Engine permanecem intocados.
