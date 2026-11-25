"""Regressões offline da sessão/cache do site, sem importar o app Streamlit."""
from __future__ import annotations

import ast
import copy
from pathlib import Path
from types import SimpleNamespace
import unittest

from document_runtime_service import cache_get_or_build


def _contains_literal(node, value):
    return any(
        isinstance(child, ast.Constant) and child.value == value
        for child in ast.walk(node)
    )


class TestSiteReleaseCacheHF52(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app_path = Path(__file__).resolve().with_name("app.py")
        tree = ast.parse(app_path.read_text(encoding="utf-8"), filename=str(app_path))
        version_key = "site_hf59_preview_app_version"

        guards = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.If) and _contains_literal(node.test, version_key)
        ]
        if len(guards) != 1:
            raise AssertionError("Esperado um único bloco real de invalidação da prévia por versão.")
        cls.invalidation_code = compile(
            ast.Module(body=[guards[0]], type_ignores=[]), str(app_path), "exec"
        )

        version_writes = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(_contains_literal(target, version_key) for target in node.targets)
        ]
        if len(version_writes) != 1:
            raise AssertionError("Esperado um único registro da versão da prévia gerada.")
        cls.version_record_code = compile(
            ast.Module(body=[version_writes[0]], type_ignores=[]), str(app_path), "exec"
        )

        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_document_cache_get_or_build"
            and len(node.args) >= 3
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value == "site-producao-bundle-hf59"
        ]
        if len(calls) != 1:
            raise AssertionError("Esperada uma única chamada real do cache do pacote de produção.")
        call = calls[0]
        cls.cache_namespace = ast.literal_eval(call.args[1])
        cls.payload_code = compile(ast.Expression(body=call.args[2]), str(app_path), "eval")
        cls.cache_options = {
            keyword.arg: ast.literal_eval(keyword.value)
            for keyword in call.keywords
        }

    @staticmethod
    def _session():
        return {
            "site_hf59_html_preview": "<html>prévia existente</html>",
            "site_hf59_confirmar_publicacao": True,
            "site_hf59_preview_app_version": "HF65.24.51",
            "pedido_em_edicao": {"numero": "TESTE-1", "itens": ["caneca"]},
            "usuario_logado": "usuario-de-teste",
            "site_hf44_ultimo_fingerprint": "publicacao-anterior",
            "_site_runtime_cache_hf45": {"dados_auxiliares": [1, 2, 3]},
        }

    def _execute(self, code, session, version="HF65.24.52"):
        exec(code, {
            "__builtins__": {},
            "st": SimpleNamespace(session_state=session),
            "APP_VERSION": version,
        })

    def test_old_or_unversioned_preview_loses_only_preview_and_confirmation(self):
        for has_version in (True, False):
            with self.subTest(has_version=has_version):
                state = self._session()
                if not has_version:
                    state.pop("site_hf59_preview_app_version")
                expected = copy.deepcopy(state)
                expected.pop("site_hf59_html_preview")
                expected.pop("site_hf59_confirmar_publicacao")
                order = state["pedido_em_edicao"]
                other_cache = state["_site_runtime_cache_hf45"]

                self._execute(self.invalidation_code, state)

                self.assertEqual(state, expected)
                self.assertIs(state["pedido_em_edicao"], order)
                self.assertIs(state["_site_runtime_cache_hf45"], other_cache)
                # O próximo rerun, antes de gerar outra prévia, é idempotente.
                self._execute(self.invalidation_code, state)
                self.assertEqual(state, expected)

    def test_preview_recorded_for_current_release_survives_rerun(self):
        state = self._session()
        self._execute(self.version_record_code, state)
        self.assertEqual(state["site_hf59_preview_app_version"], "HF65.24.52")
        expected = copy.deepcopy(state)
        preview = state["site_hf59_html_preview"]
        order = state["pedido_em_edicao"]

        self._execute(self.invalidation_code, state)

        self.assertEqual(state, expected)
        self.assertIs(state["site_hf59_html_preview"], preview)
        self.assertIs(state["pedido_em_edicao"], order)
        self.assertTrue(state["site_hf59_confirmar_publicacao"])

    def test_real_payload_rebuilds_for_new_release_and_reuses_same_release(self):
        context = {
            "__builtins__": {},
            "catalogo_site_hf35": [{"id": "TESTE-1", "nome": "Caneca"}],
            "empresa_vitrine_hf59": {"nome": "Empresa de teste"},
            "logo_src_hf59": "logo-de-teste",
            "galeria_site_hf59": [{"produto": "Caneca", "imagem": "foto-de-teste"}],
            "resumo_vitrine_hf59": {"total": 1},
            "campanha_hf65": {"enabled": False},
            "home_hf6514": {"banners": []},
            "_adsense_id_hf6520": "",
            "_dicas_hf6522": [],
            "_posts_hf652417": [],
        }
        cache = {"dados_auxiliares": {"preservar": True}}
        auxiliary = cache["dados_auxiliares"]
        builds = []

        def build_package():
            builds.append(len(builds) + 1)
            number = builds[-1]
            return f"<html>pacote {number}</html>", f"ZIP de teste {number}".encode()

        def get_package(version, now):
            payload = eval(self.payload_code, dict(context, APP_VERSION=version))
            return cache_get_or_build(
                cache, self.cache_namespace, payload, build_package,
                now=now, **self.cache_options,
            )

        old_package, old_hit = get_package("HF65.24.51", 1000)
        old_again, old_again_hit = get_package("HF65.24.51", 1001)
        new_package, new_hit = get_package("HF65.24.52", 1002)
        new_again, new_again_hit = get_package("HF65.24.52", 1003)

        self.assertFalse(old_hit)
        self.assertTrue(old_again_hit)
        self.assertIs(old_package, old_again)
        self.assertFalse(new_hit)
        self.assertNotEqual(new_package, old_package)
        self.assertTrue(new_again_hit)
        self.assertIs(new_package, new_again)
        self.assertEqual(builds, [1, 2])
        self.assertIs(cache["dados_auxiliares"], auxiliary)


if __name__ == "__main__":
    unittest.main()
