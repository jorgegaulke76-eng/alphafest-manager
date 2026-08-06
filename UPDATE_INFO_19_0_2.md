# AlphaFest Manager 19.0.2

## Correção definitiva de versão e integração do Marketing Studio

- `APP_VERSION` passa a ser lida diretamente de `VERSAO.txt`.
- Elimina divergência entre a versão exibida no Streamlit e a versão publicada.
- Mantém `AlphaFest Agência — Padrão Anna ⭐` como template padrão.
- Mantém os modos de foto: Automático, Preservar foto inteira e Remover fundo.
- Confirma integração do parâmetro `photo_mode` entre `app.py` e `marketing_template_engine.py`.
- Mantém compatibilidade com campanhas antigas salvas como `alphafest_agencia`.
