# AlphaFest Manager 20.0.0 — Template Engine

- Biblioteca de templates instaláveis sem alteração de Python.
- Novo módulo `template_library_engine.py`.
- Estrutura `templates/<id>/fundo.png + layout.json + config.json + preview.png`.
- Template `Anna Base Dinâmica` incluído como primeiro modelo da nova arquitetura.
- Templates externos aparecem automaticamente no seletor do Marketing Studio.
- Importação de pacote ZIP pelo próprio Marketing Studio.
- Exportação de templates instalados em ZIP.
- Renderização por zonas normalizadas, preservando a proporção da foto.
- Base preparada para o futuro Editor Visual de zonas.

- Templates importados pela interface são persistidos no armazenamento do Marketing Studio e restaurados após reboot do Streamlit.
