# AlphaFest Manager 20.4.9-I8.13.5-HF12

## Correção de inicialização da HF11

- Corrige o `ImportError` na inicialização do Streamlit introduzido pela HF11.
- A prévia visual do produto no Orçamento permanece disponível.
- O `app.py` deixa de exigir o novo símbolo `midias_preview_catalogo` no import do service.
- A leitura das mídias usada pela prévia passa a ter uma camada local compatível com o `catalogo_orcamento_service` anterior, protegendo contra atualização parcial dos arquivos no deploy.
- Não altera dados operacionais, Catálogo Oficial, clientes, propostas, estoque ou status.

## Homologação sugerida

1. Confirmar que o aplicativo inicia normalmente.
2. Abrir Novo Orçamento.
3. Selecionar um produto do Catálogo com foto e confirmar a prévia visual.
