# AlphaFest Manager — HF26 Organização interna II

## Objetivo
Continuar a separação gradual e conservadora do `app.py`, sem alterar telas ou regras.

## Alterações
- Saúde do sistema isolada em `system_health_ui.py`;
- Boot Manager isolado no mesmo módulo;
- `app.py` apenas injeta as funções existentes;
- novo módulo incluído nas verificações obrigatórias e na compilação crítica de release;
- HF7, Template Anna e Marketing Engine preservados.
