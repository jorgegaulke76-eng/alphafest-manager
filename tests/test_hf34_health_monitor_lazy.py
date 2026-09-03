import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"


class HF34HealthMonitorLazyTests(unittest.TestCase):
    def test_sob_demanda_e_estado_saudavel_do_monitor(self):
        src = APP.read_text(encoding="utf-8")
        self.assertIn('estados_saudaveis_monitor = {"ok", "contingencia", "isolado", "sob demanda"}', src)
        self.assertIn('str(item.get("status", "ok")) == "sob demanda"', src)

    def test_monitor_explica_carga_sob_demanda_sem_alerta(self):
        src = APP.read_text(encoding="utf-8")
        self.assertIn('módulo(s) aguardando uso — carga sob demanda normal', src)
        self.assertIn('verificações saudáveis', src)

    def test_import_lazy_atualiza_mesma_etapa_do_diagnostico(self):
        src = APP.read_text(encoding="utf-8")
        self.assertIn('registrar_boot("Alpha Intelligence", "ok"', src)
        self.assertIn('registrar_boot("Central de oportunidades", "ok"', src)
        self.assertNotIn('registrar_boot("Alpha Intelligence (sob demanda)"', src)
        self.assertNotIn('registrar_boot("Central de oportunidades (sob demanda)"', src)

    def test_performance_hf33_permanece(self):
        src = APP.read_text(encoding="utf-8")
        self.assertIn('Carregado somente ao abrir o módulo.', src)
        self.assertIn('Carregada somente ao abrir Atendimento > Oportunidades.', src)
        self.assertTrue((ROOT / "lazy_runtime.py").exists())


if __name__ == "__main__":
    unittest.main()
