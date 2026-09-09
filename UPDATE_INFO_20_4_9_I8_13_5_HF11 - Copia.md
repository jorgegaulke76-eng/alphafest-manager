# 20.4.9-I8.13.5-HF11 — Confirmação visual do produto no Orçamento

Base: **20.4.9-I8.13.5-HF10 homologada**.

## Objetivo
Fechar a integração visual entre Novo Orçamento e Catálogo Oficial: depois de selecionar/reconhecer um produto do Catálogo, Jorge e Anna podem confirmar visualmente o item antes de adicioná-lo à proposta.

## Comportamento
- Produto do Catálogo selecionado/reconhecido: mantém o preço oficial automático já homologado.
- Exibe a **foto principal** cadastrada no Catálogo diretamente no Orçamento.
- Quando houver outras fotos, oferece uma galeria recolhida para conferência sob demanda.
- Quando houver vídeo público, oferece acesso ao vídeo do produto; vídeo local continua apenas sinalizado, sem bloquear o orçamento.
- Produto sem mídia continua funcionando normalmente e recebe apenas um aviso discreto.
- Produto livre/novo continua permitido e não recebe vínculo visual inventado.
- A mesma confirmação visual vale para os fluxos de Jorge e Anna.

## Regras preservadas
Continuam **sempre manuais** e nunca são preenchidos pela galeria:
- Tema / Ocasião;
- Nome(s) personalizado(s);
- Cor / Material do pedido;
- Idade / Data do Evento;
- Outros Detalhes.

Também permanecem preservados:
- reconhecimento/cadastro de cliente da HF9/HF10;
- Perfil Comercial e preços especiais;
- Catálogo Oficial e galeria existente de até 5 mídias;
- status Aprovado/Pago/Pronto/Entregue;
- materiais, estoque, produção, entregas e histórico.

## Integridade
- A prévia é somente leitura e não modifica o produto do Catálogo.
- A primeira foto continua sendo a principal.
- O vídeo conta dentro do limite visual de 5 mídias.
- Referências duplicadas de foto são ignoradas apenas na montagem da prévia, sem regravar o cadastro.
- `VERSAO` e `VERSAO.txt` foram alinhados em **20.4.9-I8.13.5-HF11**.

## Homologação sugerida
1. Abrir **Novo Orçamento**.
2. Escolher um produto do Catálogo que possua foto.
3. Confirmar que a foto principal aparece antes de adicionar o item.
4. Se o produto tiver mais fotos, abrir **Ver outras fotos** e conferir a galeria.
5. Confirmar que o preço oficial foi carregado e que Tema, Nome, Cor/Material e Outros Detalhes continuam vazios/manuais.
6. Adicionar o item e salvar a proposta normalmente.

## Testes
- **66 testes automáticos aprovados**.
- Incluídos testes específicos de primeira foto, deduplicação de mídia, limite com vídeo, produto sem mídia e garantia de somente leitura.
