# HF65.24.6 — correção de inicialização (ImportError)

- Base: HF65.24.5.
- Restaura `youtube_export_text` em `site_dicas_multicanal_service.py`, exportação usada pelo `app.py` e omitida na HF65.24.3–5.
- Mantém a seção de depoimentos em texto, imagem e vídeo e a correção da interface de upload da HF65.24.5.
- Não altera dados ou Secrets do Supabase/YouTube.
- Validado: importação do módulo de dicas; execução de exportação de texto do YouTube; renderização dos três formatos de depoimento; compilação dos fontes Python.
- Requer teste de inicialização no Streamlit Cloud após instalação; nenhum deploy automático.
