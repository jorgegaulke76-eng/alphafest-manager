"""Entrada isolada para deploy de homologação Streamlit HF65.24.53.

Sem import de app.py do Manager e sem consultas financeiras.
A página principal permanece na raiz do repositório para testes unitários.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from hf65_24_53_homologacao_login import render
from hf65_24_53_http_diagnostic import render_http_diagnostic, render_session_write_diagnostic

st.set_page_config(page_title="AlphaFest HF65.24.53 — Login teste")
render(st)
render_http_diagnostic(st)
render_session_write_diagnostic(st)
