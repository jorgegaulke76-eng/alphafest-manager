"""Regressões offline de conteúdo conferido e conflitos editoriais reais."""
from __future__ import annotations

import ast
import copy
from datetime import date, datetime
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import requests
import cloud_db

import site_integrity_service as integrity


def payload():
    return {
        "versao_manager": "release-atual", "catalogo": [{"id": "caneca", "Nome": "Caneca"}],
        "empresa": {"nome": "Loja teste"}, "logo": "logo", "galeria": [{"id": "foto-1"}],
        "total": 1, "visual": "HF65", "campaign": {"enabled": False}, "home": {"banners": []},
        "adsense": "", "dicas": [], "posts": [], "data_publicacao": "2026-11-25",
    }


class TestPreviewIntegrity(unittest.TestCase):
    def setUp(self):
        self.state = {"pedido_em_edicao": {"numero": "TESTE", "itens": ["Caneca"]}}
        self.content = payload()
        integrity.remember_preview(self.state, "<html>Conferida</html>", "release-atual", self.content)
        self.state[integrity.CONFIRMATION] = True

    def test_every_package_input_invalidates_old_confirmation(self):
        for key, value in self.content.items():
            with self.subTest(input=key):
                changed = copy.deepcopy(self.content)
                changed[key] = ["alterado"] if isinstance(value, list) else {"alterado": True}
                state = copy.deepcopy(self.state)
                self.assertTrue(integrity.invalidate_changed_preview(state, "release-atual", changed))
                self.assertFalse(integrity.preview_matches(state, "release-atual", changed))
                self.assertNotIn(integrity.CONFIRMATION, state)
                self.assertEqual(state["pedido_em_edicao"], self.state["pedido_em_edicao"])

    def test_same_content_rerun_keeps_review_and_confirmation(self):
        original = copy.deepcopy(self.state)
        self.assertFalse(integrity.invalidate_changed_preview(self.state, "release-atual", dict(reversed(list(self.content.items())))))
        self.assertEqual(self.state, original)

    def test_rebuild_requires_new_confirmation(self):
        integrity.remember_preview(self.state, "<html>Reconstruída</html>", "release-atual", self.content)
        self.assertNotIn(integrity.CONFIRMATION, self.state)
        self.assertTrue(integrity.preview_matches(self.state, "release-atual", self.content))

    def test_legacy_preview_without_signature_is_not_publishable(self):
        self.state.pop(integrity.PREVIEW_SIGNATURE)
        self.assertTrue(integrity.invalidate_changed_preview(self.state, "release-atual", self.content))
        self.assertNotIn(integrity.PREVIEW_HTML, self.state)

    def test_new_release_drops_old_preview(self):
        self.assertTrue(integrity.invalidate_changed_preview(self.state, "release-nova", self.content))
        self.assertNotIn(integrity.CONFIRMATION, self.state)

    def test_empty_generation_does_not_replace_last_preview(self):
        original = copy.deepcopy(self.state)
        with self.assertRaises(ValueError):
            integrity.remember_preview(self.state, "", "release-atual", self.content)
        self.assertEqual(self.state, original)


class StopRender(Exception):
    pass


class FakeStreamlit:
    def __init__(self):
        self.session_state = {}
        self.messages = []
        self.downloads = []

    def error(self, message):
        self.messages.append(message)

    info = error

    def download_button(self, *args, **kwargs):
        self.downloads.append(kwargs)

    def stop(self):
        raise StopRender()


class FakeCloud:
    def __init__(self):
        self.documents = {}
        self.expected = []
        self.unguarded_writes = 0

    def load_document(self, key, path, default):
        return copy.deepcopy(self.documents.get(key, default))

    def save_document_cas(self, key, expected, value, path):
        self.expected.append(copy.deepcopy(expected))
        if self.documents.get(key) != expected:
            return False, "conflito: documento alterado em outra sessão"
        self.documents[key] = copy.deepcopy(value)
        return True, "online"

    def save_document(self, *args):
        self.unguarded_writes += 1
        raise AssertionError("Documento editorial não pode usar gravação sem conferência")


class TestRealEditorialWrites(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tree = ast.parse(Path(__file__).with_name("app.py").read_text(encoding="utf-8"))
        names = {"_document_cache", "invalidate_document_cache", "load_document", "save_document", "_carregar_editorial_site_hf53"}
        selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
        if {node.name for node in selected} != names:
            raise AssertionError("Funções reais de persistência ausentes")
        cls.code = compile(ast.Module(body=selected, type_ignores=[]), "app.py", "exec")

    def session(self, cloud):
        st = FakeStreamlit()
        context = {
            "st": st, "_cloud_db": cloud, "copy": copy, "json": json, "datetime": datetime,
            "time": SimpleNamespace(monotonic=lambda: 1000), "DOCUMENT_CACHE_TTL_SECONDS": 30,
            "_site_editorial_keys_hf53": integrity.EDITORIAL_DOCUMENT_KEYS,
            "_site_editorial_expected_hf53": integrity.editorial_expected,
            "_site_editorial_snapshot_hf53": integrity.editorial_snapshot,
            "_site_editorial_saved_hf53": integrity.editorial_saved,
            "_site_remember_draft_hf53": integrity.remember_editorial_draft,
        }
        exec(self.code, context)
        return st, context

    def test_concurrent_edit_after_cache_refresh_preserves_draft_and_remote(self):
        for key in sorted(integrity.EDITORIAL_DOCUMENT_KEYS):
            with self.subTest(document=key):
                cloud = FakeCloud()
                cloud.documents[key] = {"texto": "original"}
                st1, session1 = self.session(cloud)
                st2, session2 = self.session(cloud)
                for session in (session1, session2):
                    self.assertEqual(session["_carregar_editorial_site_hf53"](key, "unused", {}), {"texto": "original"})
                self.assertTrue(session1["save_document"](key, {"texto": "primeira sessão"}, "unused"))
                # Um novo GET/TTL não deve substituir a base dos campos já abertos.
                session2["load_document"](key, "unused", {}, force_refresh=True)
                self.assertEqual(session2["_carregar_editorial_site_hf53"](key, "unused", {}), {"texto": "original"})
                draft = {"texto": "segunda sessão", "itens": ["rascunho"]}
                with self.assertRaises(StopRender):
                    session2["save_document"](key, draft, "unused")
                self.assertEqual(cloud.documents[key], {"texto": "primeira sessão"})
                self.assertEqual(cloud.expected[-1], {"texto": "original"})
                self.assertEqual(st2.session_state["_site_editorial_drafts_hf53"][key], draft)
                self.assertFalse(st2.session_state["_last_write_status"]["ok"])
                self.assertEqual(json.loads(st2.downloads[0]["data"]), draft)
                draft["itens"].append("alteração posterior")
                self.assertEqual(st2.session_state["_site_editorial_drafts_hf53"][key]["itens"], ["rascunho"])
                self.assertEqual(cloud.unguarded_writes, 0)

    def test_explicit_refresh_keeps_recovery_and_uses_new_base(self):
        key = "site_home_content_db"
        cloud = FakeCloud()
        cloud.documents[key] = {"texto": "original"}
        st, session = self.session(cloud)
        session["_carregar_editorial_site_hf53"](key, "unused", {})
        integrity.remember_editorial_draft(st.session_state, key, {"texto": "rascunho"})
        st.session_state["pedido_em_edicao"] = {"id": "preservado"}
        cloud.documents[key] = {"texto": "novo remoto"}
        integrity.refresh_editorial_bases(st.session_state)
        self.assertIn(key, st.session_state["_site_editorial_drafts_hf53"])
        self.assertEqual(session["_carregar_editorial_site_hf53"](key, "unused", {}, force_refresh=True), {"texto": "novo remoto"})
        self.assertTrue(session["save_document"](key, {"texto": "mesclado após revisar"}, "unused"))
        self.assertEqual(cloud.expected[-1], {"texto": "novo remoto"})
        self.assertNotIn(key, st.session_state["_site_editorial_drafts_hf53"])
        self.assertEqual(st.session_state["pedido_em_edicao"], {"id": "preservado"})

    def test_missing_base_does_not_write_without_guard(self):
        cloud = FakeCloud()
        st, session = self.session(cloud)
        self.assertFalse(session["save_document"]("site_home_content_db", {"texto": "novo"}, "unused", stop_on_error=False))
        self.assertEqual(cloud.documents, {})
        self.assertEqual(cloud.unguarded_writes, 0)


class TestProductionSnapshot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tree = ast.parse(Path(__file__).with_name("app.py").read_text(encoding="utf-8"))
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "_ler_payload_site_hf53"]
        if len(functions) != 1:
            raise AssertionError("Leitura única do payload não encontrada")
        cls.code = compile(ast.Module(body=functions, type_ignores=[]), "app.py", "exec")

    def test_final_snapshot_reads_saved_documents_with_forced_refresh(self):
        documents = {key: {"marcador": key} for key in integrity.EDITORIAL_DOCUMENT_KEYS}
        documents.update({"catalogo_db": [{"id": "p1"}], "galeria_trabalhos_db": [], "config_empresa": {"nome": "Salvo"}, "site_adsense_db": {"publisher_id": ""}})
        calls = []

        def load(key, path, default, force_refresh=False):
            calls.append((key, force_refresh))
            return copy.deepcopy(documents[key])

        context = {
            "load_document": load, "APP_VERSION": "release-atual", "logo_src_hf59": "logo",
            "CONFIG_EMPRESA_PADRAO": {"nome": "padrão"}, "hoje_local": lambda: date(2026, 11, 25),
            "_site_resumir_vitrine": lambda records, **kw: {"total": len(records)},
        }
        for name in ("CATALOGO", "GALERIA_TRABALHOS", "EMPRESA", "SITE_CAMPAIGN", "SITE_HOME_CONTENT", "SITE_ADSENSE", "SITE_DICAS", "SITE_POSTS"):
            context["ARQUIVO_" + name] = "unused"
        for name in ("campaign", "home", "adsense", "dicas", "posts"):
            context["_site_" + name + "_normalize"] = lambda value: value
            context["_site_" + name + "_default"] = {}
        exec(self.code, context)
        current = context["_ler_payload_site_hf53"](force_refresh=True)
        self.assertEqual(len(calls), 8)
        self.assertTrue(all(force for _, force in calls))
        self.assertEqual(current["empresa"]["nome"], "Salvo")
        self.assertEqual(current["total"], 1)
        self.assertEqual(current["data_publicacao"], "2026-11-25")
        state = {}
        integrity.remember_preview(state, "<html>prévia</html>", "release-atual", current)
        documents["catalogo_db"].append({"id": "p2"})
        newer = context["_ler_payload_site_hf53"](force_refresh=True)
        self.assertFalse(integrity.preview_matches(state, "release-atual", newer))

        confirmed_calls = []
        def confirmed(key, default=None):
            confirmed_calls.append(key)
            return copy.deepcopy(documents[key])
        context["_cloud_db"] = SimpleNamespace(load_document_confirmed=confirmed)
        before = len(calls)
        self.assertEqual(context["_ler_payload_site_hf53"](require_online=True), newer)
        self.assertEqual(len(confirmed_calls), 8)
        self.assertEqual(len(calls), before, "Publicação não pode passar pelo leitor com fallback")
        context["_cloud_db"] = SimpleNamespace(load_document_confirmed=Mock(side_effect=RuntimeError("leitura não confirmada")))
        with self.assertRaisesRegex(RuntimeError, "não confirmada"):
            context["_ler_payload_site_hf53"](require_online=True)


class TestConfirmedCloudRead(unittest.TestCase):
    def read_with_response(self, response, default=None):
        with patch.object(cloud_db, "online_configured", return_value=True), \
             patch.object(cloud_db, "_config", return_value=("https://example.invalid", "test-only")), \
             patch.object(cloud_db._SESSION, "get", return_value=response) as get, \
             patch.object(cloud_db, "_read_local", side_effect=AssertionError("não ler fallback")), \
             patch.object(cloud_db, "save_document", side_effect=AssertionError("não gravar")):
            result = cloud_db.load_document_confirmed("site_home_content_db", default)
            self.assertEqual(get.call_count, 1)
            return result

    def test_reads_confirmed_value_and_never_local_copy(self):
        response = Mock()
        response.json.return_value = [{"value": {"texto": "salvo online"}}]
        self.assertEqual(self.read_with_response(response, {"texto": "default"}), {"texto": "salvo online"})

    def test_confirmed_absence_uses_independent_explicit_default(self):
        response = Mock()
        response.json.return_value = []
        default = {"itens": []}
        result = self.read_with_response(response, default)
        result["itens"].append("alteração")
        self.assertEqual(default, {"itens": []})

    def test_network_failure_never_authorizes_local_fallback(self):
        with patch.object(cloud_db, "online_configured", return_value=True), \
             patch.object(cloud_db, "_config", return_value=("https://example.invalid", "test-only")), \
             patch.object(cloud_db._SESSION, "get", side_effect=requests.ConnectionError()), \
             patch.object(cloud_db, "_read_local", side_effect=AssertionError("não ler fallback")):
            with self.assertRaisesRegex(RuntimeError, "Não foi possível confirmar"):
                cloud_db.load_document_confirmed("site_home_content_db", {"texto": "default"})

    def test_malformed_response_never_becomes_default(self):
        for rows in ({"error": "failed"}, [None], [{}]):
            with self.subTest(rows=rows):
                response = Mock()
                response.json.return_value = rows
                with self.assertRaisesRegex(RuntimeError, "Não foi possível confirmar"):
                    self.read_with_response(response, {"texto": "default"})

    def test_unconfigured_cloud_cannot_confirm_publication(self):
        with patch.object(cloud_db, "online_configured", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "não está disponível"):
                cloud_db.load_document_confirmed("site_home_content_db", {})


if __name__ == "__main__":
    unittest.main()
