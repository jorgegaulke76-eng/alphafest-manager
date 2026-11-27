"""Integra HF61 apenas se app.py corresponder a HF60."""
from pathlib import Path
import ast, subprocess
p = Path(__file__).resolve().parents[1] / "app.py"
sha = subprocess.check_output(["git", "hash-object", str(p)], text=True).strip()
if sha != "a92fb792f8e0b57d16033d3be5c3769a464a462d":
    raise RuntimeError("app.py inesperado: abortando para preservar dados")
s = p.read_text(encoding="utf-8")
def troca(a,b):
    global s
    if s.count(a) != 1:
        raise RuntimeError("Ancora ausente ou duplicada")
    s=s.replace(a,b)
troca('from config import APP_VERSION, DATA_VERSION, DEFAULT_TIMEZONE, DOCUMENT_CACHE_TTL_SECONDS, CONNECTION_CACHE_TTL_SECONDS, APP_RELEASE_DISPLAY\n',
      'from config import APP_VERSION, DATA_VERSION, DEFAULT_TIMEZONE, DOCUMENT_CACHE_TTL_SECONDS, CONNECTION_CACHE_TTL_SECONDS, APP_RELEASE_DISPLAY\nfrom resumo_operacional_hf61_service import montar_resumo_anna as _resumo_diario_hf61\n')
troca('''    # Mesmas engines da Central, derivadas desta leitura do Histórico e das etapas do Fluxo.
    planos_hf53 = _hf53_montar_planejamentos''',
'''    # HF61: somente leitura, usando os quatro indicadores que ja estao na tela.
    with st.expander("📋 Resumo do dia · copiar ou baixar", expanded=False):
        st.caption("Totais e prioridades, sem nomes, telefones ou valores.")
        resumo_txt_hf61 = _resumo_diario_hf61(
            hoje_anna_hf40, novos=qtd_novos,
            aguardando=qtd_aguardando, ativos=len(ativos),
            entregas=qtd_entregas,
        )
        st.code(resumo_txt_hf61, language=None)
        st.download_button(
            "⬇️ Baixar resumo (.txt)",
            data=resumo_txt_hf61.encode("utf-8"),
            file_name=f"ALPHAFEST_RESUMO_{hoje_anna_hf40:%Y-%m-%d}.txt",
            mime="text/plain", key="anna_resumo_diario_hf61",
            width="stretch",
        )

    # Mesmas engines da Central, derivadas desta leitura do Histórico e das etapas do Fluxo.
    planos_hf53 = _hf53_montar_planejamentos''')
ast.parse(s)
p.write_text(s, encoding="utf-8")
print("HF61 integrada apenas na Central da Anna.")
