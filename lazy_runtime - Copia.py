"""Carregamento sob demanda de módulos opcionais/pesados do AlphaFest Manager.

HF33 — Performance sem criar uma segunda verdade de dados.
Este utilitário não faz cache de documentos operacionais. Ele apenas adia imports
custosos até a tela/função que realmente precisa deles ser usada.
"""
from __future__ import annotations

import importlib
import threading
from typing import Any


class LazyModule:
    """Proxy thread-safe que importa um módulo apenas no primeiro atributo usado."""

    __slots__ = ("_module_name", "_module", "_lock")

    def __init__(self, module_name: str):
        self._module_name = str(module_name)
        self._module = None
        self._lock = threading.RLock()

    @property
    def module_name(self) -> str:
        return self._module_name

    @property
    def loaded(self) -> bool:
        return self._module is not None

    def load(self):
        module = self._module
        if module is not None:
            return module
        with self._lock:
            module = self._module
            if module is None:
                module = importlib.import_module(self._module_name)
                self._module = module
        return module

    def __getattr__(self, name: str) -> Any:
        return getattr(self.load(), name)

    def __repr__(self) -> str:
        state = "loaded" if self.loaded else "deferred"
        return f"<LazyModule {self._module_name!r} ({state})>"
