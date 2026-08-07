# 20.4.6-D — Editor Visual Cloud Seguro

Base oficial: Atual 2046C enviada e testada.

Correção:
- declare_component agora aponta para components/alphafest_drag_box.
- frontend contém index.html próprio.
- editor não usa CDN, npm, Fabric.js ou streamlit-drawable-canvas.
- comunicação com Streamlit é feita pelo protocolo do componente no próprio JavaScript.
- arrastar, redimensionar e girar permanecem disponíveis.
- ajuste numérico continua como fallback.
- demais módulos do AlphaFest não foram alterados.
