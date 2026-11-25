"""Smoke test: a demonstracao visual abre com o Streamlit real e dados ficticios."""
from __future__ import annotations
import unittest
from pathlib import Path

try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None

ROOT = Path(__file__).resolve().parent
DEMO = ROOT / ".github" / "homologacao_hf58" / "demo.py"


@unittest.skipIf(AppTest is None, "Requer Streamlit AppTest real")
class DemoIsoladaHF58SmokeTest(unittest.TestCase):
    def test_abre_demo_local_sem_pedido_real(self):
        self.assertTrue(DEMO.is_file())
        at = AppTest.from_file(str(DEMO), default_timeout=25).run()
        self.assertEqual([e.message for e in at.exception], [])
        projeto = at.session_state["projeto"]
        proposta = at.session_state["proposta"]
        self.assertEqual(projeto["id"], "PRJ-HF58-DEMONSTRACAO")
        self.assertEqual(proposta["numero_proposta"], "PEDIDO-FICTICIO-HF58")
        self.assertEqual(proposta["status"], "Em andamento")
        self.assertFalse(proposta["aprovado"])
        self.assertEqual(at.session_state["hf58_demo_gravacoes"], 0)
        self.assertEqual(len(proposta["itens"]), 2)
        self.assertEqual(at.session_state["hf58_demo_uploads"], 0)

if __name__ == "__main__":
    unittest.main()
