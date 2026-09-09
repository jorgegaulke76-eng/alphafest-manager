# 20.4.8-B — Hotfix de estabilidade da Central

Base: Atual 2048A.

- mantém a busca precisa do THU;
- corrige o fluxo do botão Mostrar na Central;
- a seleção do THU agora é aplicada antes da criação dos widgets da Central;
- evita mutação de widgets já renderizados no mesmo ciclo do Streamlit;
- reduz o erro de reconciliação front-end removeChild observado após a navegação;
- demais módulos e dados preservados.
