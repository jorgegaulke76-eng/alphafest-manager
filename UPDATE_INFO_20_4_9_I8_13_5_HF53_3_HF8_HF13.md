# HF53.3-HF8-HF13 — Trava de runtime e seleção do Template Anna

- Corrige o retorno acidental ao Template Mestre após reinício/atualização do Streamlit: o `Template Anna — Redes Sociais` passa a ser o padrão da tela do Piloto Automático nesta etapa.
- O Template Mestre Comercial HF7 continua disponível, oficial, protegido e congelado; nenhuma composição ou asset do HF7 foi alterado.
- O Template Anna passa a usar `marketing_anna_renderer_hf11.py`, módulo dedicado e versionado, evitando que o fluxo recaia no renderer legado.
- O motor registra a versão realmente carregada do renderer Anna (`HF53.3-HF8-HF11`) em `renderer_runtime_version` e na origem de novas campanhas Anna.
- A interface exibe o renderer usado nas campanhas Anna para facilitar conferência.
- A composição do Modelo Anna 1 protege a manchete `Gravação Laser` e o selo emocional para que o palco/foto não os cubra.
- `VERSAO` e `VERSAO.txt` ficam sincronizados em `20.4.9-I8.13.5-HF53.3-HF8-HF13`.
