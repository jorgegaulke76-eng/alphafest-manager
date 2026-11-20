# HF65.24.43 — Compatibilidade e estabilidade da interface

- Substituídos aproximadamente 540 usos obsoletos de `use_container_width` pela API suportada `width` do Streamlit.
- Preservada a largura fixa de 340 pixels na prévia de arte em Novidades.
- Definida versão mínima do Streamlit (>=1.51,<2), compatível com a API `width`.
- Não alterados banco de dados, Secrets, status, pedidos, catálogo ou publicação do site.
- A redução de avisos nos logs não garante a eliminação de timeouts: se eles persistirem, consultar Logs no Streamlit Cloud.
- Não executar alterações nos pedidos durante desconexões.
