# AlphaFest Manager 20.4.6-D

## Correção do Editor Visual Drag & Drop

- Corrigido o carregamento do componente `alphafest_drag_box` no Streamlit Cloud.
- O frontend agora fica em `alphafest_drag_box/index.html`, estrutura exigida por `components.declare_component(path=...)`.
- Mantidos arrastar, redimensionar, girar e retorno das coordenadas ao Python.
- Mantidos controles numéricos como ajuste fino e fallback.
- Nenhuma alteração no fluxo de orçamento, catálogo, clientes ou banco.
